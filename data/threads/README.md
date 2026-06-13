# Thread catalogs

Step 3 (thread-match) snaps each quantized color to the nearest real cone here,
matched in CIELAB.

Catalogs are **Ink-Stitch GIMP palettes (`.gpl`)**, named to match the
`--thread-chart` value:

- `madeira-polyneon.gpl`  (Ink/Stitch: Madeira Polyneon)
- `isacord.gpl`           (Ink/Stitch: Isacord Polyester)

Format — header lines then one color per row:

```
GIMP Palette
Name: Ink/Stitch: Madeira Polyneon
Columns: 4
# RGB Value          Color Name Number
183 195 197          Celestial Blue   1610
```

i.e. `R G B  <color name, may contain spaces>  <catalog code>`. The parser lives
in `src/wilcom_pipeline/catalog.py`.

Source: https://github.com/inkstitch/inkstitch/tree/main/palettes
(`InkStitch Madeira Polyneon.gpl`, `InkStitch Isacord Polyester.gpl`).
