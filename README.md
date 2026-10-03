# printgate

Checks for 3D-print models and G-code before they reach a printer.

- **`printgate gcode`** reads sliced G-code and blocks the failure modes that waste a print:
  a first layer too small to hold, parts whose brims fused, support on a mating face, geometry
  that starts in mid-air, moves off the bed or below it, a missing home, small parts that warp.
  Thresholds and bed limits come from a printer profile.
- **`printgate review`** renders OpenSCAD models, measures them, pictures them (four views plus
  an optional in-context view) and writes a pull-request comment with deltas against the base
  revision. It can slice the result and run the G-code checks too.
- **A pytest plugin** for models that guard their design rules with `assert()`: `openscad.fails`
  proves an assert fires for bad parameters, `openscad.renders` that good ones still render.

External tools plug in as adapters (mesh analysis via trimesh, slicing via PrusaSlicer, geometric
diffs via argus-diff) and output goes through reporters (text, JSON, Markdown). Both are found by
entry point, so another package can add its own.

## Use

```
pip install "printgate[mesh]"
printgate gcode plate.gcode --parts 4 --printer my-printer
printgate review models/*.scad --base-root ../base --context mode=assembly --output review.md
printgate comment review.md --pr 12     # in CI: edits the earlier report comment, or posts one
```

## Configure

Describe your printers once, in `printgate.toml` or under `[tool.printgate]` in
`pyproject.toml` (or point `PRINTGATE_CONFIG` at a file). Every printer with a slicer adds its
projected print time and filament to a review, and its own G-code findings.

```toml
[printers.my-printer]
firmware = "klipper"                     # any field of src/printgate/profile.py
bed_max = [220, 220, 280]
require_leveling = true
slicer = "prusaslicer"
slicer_config = "profiles/pla.ini"       # relative to this file
center = [110, 110]
filament_density = 1.24
```

`PRINTGATE_PRINTERS=a,b` narrows a run to those printers; `printgate config` shows what is in
effect. `printgate gcode --printer my-printer` judges against that printer's profile, and
`--profile file.toml` takes a bare profile instead.

`printgate gcode` exits 0 to print, 1 when something blocks, 2 on a usage error.
OpenSCAD is found as `openscad` and PrusaSlicer as `prusa-slicer`, or through
`PRINTGATE_OPENSCAD` and `PRINTGATE_PRUSASLICER`.

```python
def test_bracket_rejects_a_slot_too_wide(openscad):
    openscad.fails("bracket.scad", "slot wider than the rail", slot_w=25)
```

## Known limitations

- Arc moves (`G2`/`G3`) and relative positioning (`G91`) are not followed.
- The thresholds were calibrated on one bed-slinger-sized printer running PLA; profiles exist to
  override them.
- The mid-air check can flag an island that rests on support printed in the same layer.

## Status

Pre-release. Licensed under Apache-2.0.
