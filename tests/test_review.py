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
    assert r.metrics["Bodies"] == 1
    assert r.baseline == r.metrics
    assert {i.name for i in r.images} == {"iso", "top", "bed", "section", "context"}
    assert all(i.path.exists() for i in r.images)


def test_a_failed_render_blocks(openscad, tmp_path):
    scad = tmp_path / "bad.scad"
    scad.write_text("assert(false, \"nope\");\ncube(1);\n")
    r = review(scad, tmp_path / "out", TrimeshAnalyzer())
    assert [f.check for f in r.findings if f.severity is Severity.BLOCK] == ["render"]


class FakeSlicer:
    overrides = []

    def __init__(self, config, center):
        self.config = config

    def slice(self, stl, gcode, overrides=()):
        FakeSlicer.overrides.append(overrides)
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


def test_settings_beside_the_model_reach_the_slicer(openscad, tmp_path, monkeypatch):
    from printgate import plugins
    from printgate.config import Printer

    model = tmp_path / "m.scad"
    model.write_text(MODEL.read_text())
    (tmp_path / "m.fake.ini").write_text("fill_density = 100%\n")
    monkeypatch.setattr(plugins, "load", lambda group, name: FakeSlicer)
    FakeSlicer.overrides.clear()
    r = review(model, tmp_path / "out", TrimeshAnalyzer(), printers=(Printer("a", slicer="fake"),))
    assert FakeSlicer.overrides == [(tmp_path / "m.fake.ini",)]
    assert r.attachments["Slicer settings from m.fake.ini"] == "fill_density = 100%"


def test_a_part_too_big_for_a_printer_is_not_sliced_for_it(openscad, tmp_path, monkeypatch):
    from printgate import plugins
    from printgate.config import Printer
    from printgate.profile import Profile

    monkeypatch.setattr(plugins, "load", lambda group, name: FakeSlicer)
    tiny = Printer("tiny", profile=Profile(bed_max=(5, 5, 5)), slicer="fake")
    r = review(MODEL, tmp_path, TrimeshAnalyzer(), printers=(tiny,))
    assert [f.label for f in r.findings if f.check == "bed-fit"] == ["tiny/bed-fit"]
    assert not any(k.startswith("tiny:") for k in r.metrics)
