# Testing

```
pip install -e ".[mesh,test]"
pytest
```

Tests that need OpenSCAD use the `openscad` fixture and skip when it is missing; point
`PRINTGATE_OPENSCAD` at a binary to run them. Tests that need trimesh skip without it. The
review images need a display: run under `xvfb-run` on a headless machine.

## Where a test goes

A test mirrors the module it covers: `src/printgate/gcode/checks.py` is covered by
`tests/gcode/test_checks.py`.

G-code checks are tested on minimal synthetic G-code built in the test, so they stay
independent of any slicer's output. A new check comes with one test that trips it and one
near miss that does not, keyed on the check id rather than on message wording.
