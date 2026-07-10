#!/usr/bin/env python3
"""normalize_input.py — turn *any* image the user drops into a clean raster PNG the
wilcom-pipeline can ingest.

The pipeline opens its input with `PIL.Image.open` and reasons about a
border-connected background + an optional alpha channel (see src/.../imaging.py).
So the one job here is: get the user's file — whatever container it arrived in —
into a correctly-oriented 8-bit PNG, preserving a real alpha channel when the art
has one (so the pipeline can drop a transparent background) and flattening to RGB
when it doesn't.

Coverage, in order of preference (each with a graceful fallback):
  * Raster PIL already opens: PNG JPEG JPEG2000 WEBP AVIF BMP GIF TIFF PSD ICO TGA
    PPM PCX SGI DDS EPS(+Ghostscript) ...            -> opened directly
  * HEIC / HEIF (iPhone default)                     -> pillow-heif, else `heif-convert`
  * SVG (vector)                                      -> cairosvg, else `rsvg-convert`/`magick`
  * PDF (vector/page 1)                               -> `pdftoppm`, else `magick`
  * anything else PIL chokes on                       -> `magick`/`convert` universal fallback

Fidelity touches that matter for real photos:
  * EXIF orientation is applied (phone photos arrive rotated).
  * Multi-frame GIF/TIFF -> frame 0.  CMYK/16-bit/palette -> 8-bit RGB(A).
  * Vector art is rasterized big (longest side ~= --raster-px, default 2000) so thin
    strokes survive the trace.

Prints one JSON line to stdout describing what it did, so the orchestrator can read
back the true pixel size / alpha / source format and pick `--width-mm` sensibly.

Usage:
    normalize_input.py <input> [--out <file.png>] [--raster-px 2000] [--flatten-bg white|none]
If --out is omitted, writes "<input-stem>_src.png" beside the input.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

# Register the HEIF/HEIC opener into PIL if the codec is installed. Harmless if absent.
try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None

# Formats PIL will not open on its own here; we route these to a converter first.
VECTOR_SUFFIXES = {".svg", ".svgz"}
PDF_SUFFIXES = {".pdf"}


def _which(*names: str) -> str | None:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def rasterize_svg(src: Path, dst: Path, px: int) -> None:
    """SVG -> PNG at longest-side ~px. cairosvg first, then rsvg-convert, then magick."""
    try:
        import cairosvg  # type: ignore

        cairosvg.svg2png(url=str(src), write_to=str(dst), output_width=px)
        return
    except Exception:
        pass
    tool = _which("rsvg-convert")
    if tool:
        _run([tool, "-w", str(px), "-o", str(dst), str(src)])
        return
    tool = _which("magick", "convert")
    if tool:
        _run([tool, "-density", "300", "-background", "none",
              "-resize", f"{px}x{px}", str(src), str(dst)])
        return
    raise RuntimeError("SVG needs cairosvg (pip) or rsvg-convert/ImageMagick on PATH.")


def rasterize_pdf(src: Path, dst: Path, px: int) -> None:
    """PDF page 1 -> PNG. pdftoppm first (poppler), then magick+Ghostscript."""
    tool = _which("pdftoppm")
    if tool:
        with tempfile.TemporaryDirectory() as td:
            stem = Path(td) / "page"
            _run([tool, "-png", "-r", "300", "-f", "1", "-l", "1",
                  "-singlefile", str(src), str(stem)])
            produced = Path(str(stem) + ".png")
            if produced.exists():
                shutil.move(str(produced), str(dst))
                return
    tool = _which("magick", "convert")
    if tool:
        _run([tool, "-density", "300", f"{src}[0]", "-background", "white",
              "-flatten", str(dst)])
        return
    raise RuntimeError("PDF needs pdftoppm (poppler) or ImageMagick+Ghostscript on PATH.")


def convert_heic(src: Path, dst: Path) -> None:
    """HEIC/HEIF -> PNG via heif-convert when pillow-heif isn't importable."""
    tool = _which("heif-convert")
    if tool:
        _run([tool, str(src), str(dst)])
        return
    raise RuntimeError("HEIC needs pillow-heif (pip) or heif-convert (libheif) on PATH.")


def magick_fallback(src: Path, dst: Path) -> None:
    """Last resort: let ImageMagick try to decode whatever this is."""
    tool = _which("magick", "convert")
    if not tool:
        raise RuntimeError(f"cannot decode {src.name}: no PIL codec and no ImageMagick.")
    _run([tool, f"{src}[0]", str(dst)])


def load_image(src: Path, work: Path, raster_px: int) -> tuple[Image.Image, str]:
    """Return (PIL image, how_it_was_loaded). Routes vector/HEIC/exotic to converters."""
    suffix = src.suffix.lower()

    if suffix in VECTOR_SUFFIXES:
        tmp = work / "_vec.png"
        rasterize_svg(src, tmp, raster_px)
        return Image.open(tmp), "svg->png"

    if suffix in PDF_SUFFIXES:
        tmp = work / "_pdf.png"
        rasterize_pdf(src, tmp, raster_px)
        return Image.open(tmp), "pdf->png"

    # Everything else: try PIL directly (covers HEIC too when pillow-heif is registered).
    try:
        return Image.open(src), "pil"
    except Exception:
        pass

    if suffix in {".heic", ".heif"}:
        tmp = work / "_heic.png"
        convert_heic(src, tmp)
        return Image.open(tmp), "heif-convert"

    tmp = work / "_magick.png"
    magick_fallback(src, tmp)
    return Image.open(tmp), "magick"


def normalize(src: Path, dst: Path, raster_px: int, flatten_bg: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        img, how = load_image(src, work, raster_px)

        # Multi-frame (animated GIF, multipage TIFF): first frame is the design.
        try:
            img.seek(0)
        except Exception:
            pass

        img = ImageOps.exif_transpose(img)  # honour phone-camera rotation

        has_alpha = img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        )

        if has_alpha:
            img = img.convert("RGBA")
            if flatten_bg != "none":
                # Composite onto a solid so the pipeline sees a clean separable ground
                # instead of black-where-transparent. Alpha edges stay anti-aliased.
                bg = Image.new("RGBA", img.size, _bg_rgba(flatten_bg))
                img = Image.alpha_composite(bg, img).convert("RGB")
                has_alpha = False
        else:
            img = img.convert("RGB")  # collapses CMYK / 16-bit / palette to 8-bit RGB

        dst.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst, "PNG")
        return {
            "source": str(src),
            "source_format": src.suffix.lower().lstrip(".") or "unknown",
            "loaded_via": how,
            "normalized": str(dst),
            "width_px": img.width,
            "height_px": img.height,
            "aspect_w_over_h": round(img.width / img.height, 4) if img.height else None,
            "has_alpha": bool(has_alpha),
        }


def _bg_rgba(name: str) -> tuple[int, int, int, int]:
    return {"white": (255, 255, 255, 255), "black": (0, 0, 0, 255)}.get(
        name, (255, 255, 255, 255)
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--raster-px", type=int, default=2000,
                    help="Longest side for rasterized vector inputs (default 2000).")
    ap.add_argument("--flatten-bg", choices=["white", "black", "none"], default="white",
                    help="Composite transparency onto this colour (default white); "
                         "'none' keeps a real alpha channel for the pipeline to drop.")
    args = ap.parse_args(argv)

    if not args.input.is_file():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    dst = args.out or args.input.with_name(f"{args.input.stem}_src.png")
    try:
        info = normalize(args.input, dst, args.raster_px, args.flatten_bg)
    except Exception as exc:
        print(f"error: could not normalize {args.input.name}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
