# Gemini transcription prompt — Object Properties screenshots → `<design>-props.json`

Workflow: one Gemini conversation per design. Paste the prompt below + ALL of that
design's Wilcom screenshots (object-level tab shots AND whole-design Design
Information shots). Do NOT attach the .svg/.VP3 — transcription only. Save Gemini's
JSON code block as `<design>-props.json` and drop it here beside `<design>.svg` and
`<design>.VP3`. Screenshot protocol: per representative object (one per object
family), capture Fills + Pull Comp + Underlay (+ Outlines for run/border objects)
with the object SELECTED and the Color-Object List visible; plus the Design
Information panel once per design.

---

You are extracting ground-truth digitizing parameters from screenshots of Wilcom
EmbroideryStudio. Most screenshots show: (a) the "Object Properties" dialog with one
tab active, (b) the design canvas with ONE object selected, (c) the "Color-Object
List" docker where the selected object's row is highlighted with a blue box, and
(d) a status bar at the bottom reading "Object <N>: <Type>". Some screenshots
instead show a "Design Information" / "Design Properties" panel describing the
WHOLE design. These screenshots document a professional embroidery design; your
report will be machine-parsed, so follow the output format exactly.

TRANSCRIPTION RULES — these matter more than completeness:
1. Copy every number EXACTLY as displayed, with its unit (mm, %, °). Do not round,
   convert, or normalize.
2. Record the STATE of every checkbox and radio button. A value next to an UNCHECKED
   checkbox is an inactive greyed default — report it as {"enabled": false,
   "displayed_value": ...}, never as an active setting. This distinction is the main
   point of the whole exercise.
3. If a field, label, or value is not clearly readable, write "unreadable". Never
   guess or fill in typical values.
4. Do not interpret or advise. Transcribe.

FOR EACH OBJECT-LEVEL SCREENSHOT, extract:
- "file": the screenshot's filename or index in the order provided.
- "selected_object": from the status bar and the highlighted row: {"index": N,
  "type": "<as shown, e.g. Column A / Complex Fill / Run>", "stitches": N}.
- "active_tab": the highlighted tab name in Object Properties (e.g. "Pull Comp",
  "Underlay", "Fills", "Outlines", "Special", "Connectors").
- "settings": every field visible on the active tab, as nested key/value pairs,
  respecting rule 2. Include section headings (e.g. "First underlay",
  "Second underlay", "Margins") as nesting levels. Include selected radio options
  (e.g. "By segment" vs "By shape") and dropdown values (e.g. "Double Tatami").
- "selection_size_mm": the Width/Height mm fields in the top toolbar if visible.
- "canvas_location": one short phrase locating the selected object in the design
  (e.g. "top-left glyph cluster", "large fill in lower third").
- "object_list_visible_rows": the rows readable in the Color-Object List docker as
  [{"index": N, "stitches": N}] (skip the type icons if unclear).

FOR EACH DESIGN-LEVEL SCREENSHOT (Design Information / Design Properties): do not
produce a "selected_object" entry; instead fill a top-level "design" section
transcribing every visible field (Height, Width, Stitches, Colors, Stops, Trims,
Color changes, Objects, EMB version, Machine format, and any visible tab such as
Summary / Order / Thread Colors / Stitching — same transcription rules). If several
design-level screenshots show different tabs of the same panel, merge them into the
one "design" section and note which tabs were captured.

THEN produce a MERGED view: one entry per distinct selected object index, combining
the settings from all tabs captured for it.

OUTPUT FORMAT — a single JSON code block, no other text before it:
{
  "software": "<title-bar edition text if readable>",
  "machine_format": "<e.g. Tajima, from the title bar or design panel>",
  "design": { ...merged whole-design fields, plus "tabs_captured": [...]... },
  "screenshots": [ ...one entry per screenshot as specified above... ],
  "objects": [ ...merged per-object entries: {"index", "type", "stitches",
               "tabs_captured": [...], "settings": {...}}... ],
  "uncertainties": [ "...anything ambiguous, partially visible, or conflicting..." ]
}
After the JSON block, you may add at most 5 bullet points of observations (e.g.
"pull compensation is disabled on all captured objects").
