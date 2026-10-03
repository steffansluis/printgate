import pytest

trimesh = pytest.importorskip("trimesh")

from printgate.adapters.trimesh_mesh import TrimeshAnalyzer  # noqa: E402


def test_box_metrics(tmp_path):
    stl = tmp_path / "box.stl"
    trimesh.creation.box(extents=(10, 20, 5)).export(stl)
    m = TrimeshAnalyzer().analyze(stl)
    assert m["Volume (cm³)"] == pytest.approx(1.0)
    assert m["First-layer contact (mm²)"] == pytest.approx(200)
    assert m["Overhang >45° (mm²)"] == pytest.approx(0)
    assert m["Watertight"] == "yes"


def test_flat_ceiling_counts_as_overhang(tmp_path):
    stl = tmp_path / "t.stl"
    table = trimesh.util.concatenate([trimesh.creation.box((4, 4, 10)),
                                      trimesh.creation.box((20, 20, 2)).apply_translation((0, 0, 6))])
    table.export(stl)
    assert TrimeshAnalyzer().analyze(stl)["Overhang >45° (mm²)"] > 300
