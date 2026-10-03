from pathlib import Path

import pytest

pytest.importorskip("trimesh")

from printgate.adapters.trimesh_mesh import TrimeshAnalyzer  # noqa: E402
from printgate.contract import Severity  # noqa: E402
from printgate.review import parameters, review  # noqa: E402

MODEL = Path(__file__).parent / "scad" / "guarded.scad"


def test_parameters_are_literals_and_commented_assignments(tmp_path):
    scad = tmp_path / "p.scad"
    scad.write_text('a = 1;\nb = a * 2;\nc = a + 1;  // offset\nmode = "x";\n')
    assert parameters(scad) == [("a", "1", ""), ("c", "a + 1", "offset"), ("mode", '"x"', "")]


def test_review_measures_pictures_and_compares(openscad, tmp_path):
    r = review(MODEL, tmp_path, TrimeshAnalyzer(), base=MODEL, context={"width": 15, "mode": "x"})
    assert r.metrics["Volume (cm³)"] == pytest.approx(0.1)
    assert r.baseline == r.metrics
    assert {i.name for i in r.images} == {"iso", "top", "bed", "section", "context"}
    assert all(i.path.exists() for i in r.images)


def test_a_failed_render_blocks(openscad, tmp_path):
    scad = tmp_path / "bad.scad"
    scad.write_text("assert(false, \"nope\");\ncube(1);\n")
    r = review(scad, tmp_path / "out", TrimeshAnalyzer())
    assert [f.check for f in r.findings if f.severity is Severity.BLOCK] == ["render"]


class FakeSlicer:
    def __init__(self, config, center):
        self.config = config

    def slice(self, stl, gcode):
        gcode.write_text("M104 S210\nM140 S60\nG28\n;LAYER_CHANGE\nG1 Z0.2\nG1 X0 Y0 E1\n"
                         "G1 X5 Y0 E2\n; estimated printing time (normal mode) = 2m\n")
        return gcode


def test_each_printer_adds_its_time_and_findings(openscad, tmp_path, monkeypatch):
    from printgate import plugins
    from printgate.config import Printer

    monkeypatch.setattr(plugins, "load", lambda group, name: FakeSlicer)
    printers = (Printer("a", slicer="fake"), Printer("b", slicer="fake"), Printer("no-slicer"))
    r = review(MODEL, tmp_path, TrimeshAnalyzer(), printers=printers)
    assert r.metrics["a: Print time (min)"] == 2.0
    assert "b: Print time (min)" in r.metrics
    assert not any(k.startswith("no-slicer") for k in r.metrics)
    assert {"a/first-layer", "b/first-layer"} <= {f.label for f in r.findings}
    assert "first-layer" in {f.check for f in r.findings}


def test_context_needs_a_parameter_the_model_declares(openscad, tmp_path):
    r = review(MODEL, tmp_path, TrimeshAnalyzer(), context={"mode": "assembly"})
    assert "context" not in {i.name for i in r.images}
