import pytest

from printgate.gcode import preflight
from printgate.gcode.parse import estimates


@pytest.mark.parametrize("text, seconds", [
    ("; estimated printing time (normal mode) = 26m 25s\n", 1585),
    ("; estimated printing time (normal mode) = 1d 2h 3m 4s\n", 93784),
    (";TIME:1585\n", 1585),
])
def test_print_time_from_each_slicer(text, seconds):
    assert estimates(text)["seconds"] == seconds


def test_estimates_become_metrics(tmp_path):
    g = tmp_path / "g.gcode"
    g.write_text("G28\n; filament used [cm3] = 4.44\n"
                 "; estimated printing time (normal mode) = 26m 25s\n")
    m = preflight(g, filament_density=1.25).metrics
    assert m["Print time (min)"] == pytest.approx(26.4167, abs=1e-3)
    assert m["Filament (g)"] == pytest.approx(5.55)
