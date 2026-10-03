"""Each failure mode on minimal synthetic G-code, so the checks stay slicer-independent."""
import pytest

from printgate.contract import Severity
from printgate.gcode import preflight
from printgate.profile import Profile

KLIPPER = Profile(bed_max=(220, 220, 280), firmware="klipper", require_leveling=True)

# Homes and levels, sets temperatures, 30x30 first layer, no support.
HEALTHY = """M104 S210
M140 S60
G28
BED_MESH_CALIBRATE
;LAYER_CHANGE
G1 Z0.28
G1 X100 Y100 E1
G1 X130 Y100 E2
G1 X130 Y130 E3
G1 X100 Y130 E4
G1 X100 Y100 E5
;LAYER_CHANGE
G1 Z6.0
G1 X100 Y100 E6
G1 X130 Y130 E7
"""


def ids(tmp_path, gcode, severity, profile=KLIPPER, parts=None):
    p = tmp_path / "t.gcode"
    p.write_text(gcode)
    return {f.check for f in preflight(p, profile, parts).findings if f.severity is severity}


def blocks(tmp_path, gcode, **kw):
    return ids(tmp_path, gcode, Severity.BLOCK, **kw)


def warns(tmp_path, gcode, **kw):
    return ids(tmp_path, gcode, Severity.WARN, **kw)


def square(x0, y0, size, e0=1.0):
    """A travel to the corner, then a closed extruding perimeter."""
    return [f"G0 X{x0} Y{y0}", f"G1 X{x0 + size} Y{y0} E{e0 + 1}",
            f"G1 X{x0 + size} Y{y0 + size} E{e0 + 2}", f"G1 X{x0} Y{y0 + size} E{e0 + 3}",
            f"G1 X{x0} Y{y0} E{e0 + 4}"]


def column(extra_top=(), shift_top=0, support_under_top=False):
    """A 30x30 column over three layers; the top layer may shift or carry an extra island."""
    out = ["M104 S210", "M140 S60", "G28", "BED_MESH_CALIBRATE"]
    for i, z in enumerate((0.28, 0.52, 0.76)):
        out += [";LAYER_CHANGE", f"G1 Z{z}"]
        out += square(100 + (shift_top if i == 2 else 0), 100, 30, e0=10 * i + 1)
        if support_under_top and i < 2:
            out += [";TYPE:Support material", "G1 X180 Y180 E5.5", "G1 X192 Y192 E5.9",
                    ";TYPE:Perimeter"]
        if i == 2:
            out += list(extra_top)
    return "\n".join(out) + "\n"


def warping(n_parts, fan=255):
    out = ["M104 S210", "M140 S60"]
    for i in range(10):
        out += [";LAYER_CHANGE", f"G1 Z{0.28 + i * 0.24:.2f} F9000"]
        if i >= 2 and fan:
            out.append(f"M106 S{fan}")
        for p in range(n_parts):
            x0 = 100 + p * 40
            out += [f"G1 X{x0} Y100 E1 F3000", f"G1 X{x0 + 20} Y100 E2",
                    f"G1 X{x0 + 20} Y120 E3", f"G1 X{x0} Y120 E4", f"G1 X{x0} Y100 E5"]
    return "\n".join(out) + "\n"


def test_healthy_passes(tmp_path):
    assert not blocks(tmp_path, HEALTHY)


@pytest.mark.parametrize("edit, check", [
    (lambda g: "G80\n" + g, "firmware"),
    (lambda g: g.replace("G28\n", ""), "homing"),
    (lambda g: g.replace("G1 Z0.28\n", "G1 Z0.0\n"), "first-z"),
    (lambda g: g.replace("G1 Z0.28\n", "G1 Z-0.20\n"), "negative-z"),
    (lambda g: g.replace("G1 X130 Y130 E3\n", "G1 X130 Y222.1 E3\n"), "off-bed"),
    (lambda g: g.replace("G1 X100 Y100 E5\n", "G1 X100 Y100 E5\n;TYPE:Support material\n"
                                              "G1 X105 Y105 E5.1\n"), "support"),
])
def test_hazard_blocks(tmp_path, edit, check):
    assert check in blocks(tmp_path, edit(HEALTHY))


def test_upper_support_only_warns(tmp_path):
    g = HEALTHY.replace("G1 X130 Y130 E7\n", "G1 X130 Y130 E7\n;TYPE:Support material\n"
                                              "G1 X105 Y105 E7.1\n")
    assert "support" not in blocks(tmp_path, g)
    assert "support" in warns(tmp_path, g)


def test_bed_edge_is_in_range(tmp_path):
    g = HEALTHY.replace("G1 X130 Y130 E3\n", "G1 X130 Y220.0 E3\n")
    assert "off-bed" not in blocks(tmp_path, g)


def test_firmware_dialect_comes_from_the_profile(tmp_path):
    assert "firmware" not in blocks(tmp_path, "G80\n" + HEALTHY, profile=Profile())


def test_missing_mesh_warns_when_required(tmp_path):
    g = HEALTHY.replace("BED_MESH_CALIBRATE\n", "")
    assert "leveling" in warns(tmp_path, g)
    assert "leveling" not in warns(tmp_path, g, profile=Profile())


def test_tiny_first_layer_blocks(tmp_path):
    tiny = HEALTHY.replace("X130", "X102").replace("Y130", "Y102")
    assert "first-layer" in blocks(tmp_path, tiny)


def test_prime_line_is_not_the_first_layer(tmp_path):
    g = HEALTHY.replace(";LAYER_CHANGE\nG1 Z0.28\n", "G1 Z0.3\nG1 X0 Y0 E1\nG1 X1 Y0 E2\n"
                                                     ";LAYER_CHANGE\nG1 Z0.28\n", 1)
    assert "first-layer" not in blocks(tmp_path, g)


def test_fused_parts_block(tmp_path):
    assert "fusion" in blocks(tmp_path, HEALTHY, parts=2)
    assert "fusion" not in blocks(tmp_path, HEALTHY, parts=1)


def test_warp_single_small_part_blocks(tmp_path):
    assert "warp" in blocks(tmp_path, warping(1))


def test_warp_several_parts_pass(tmp_path):
    assert "warp" not in blocks(tmp_path, warping(4))


def test_midair_island_blocks(tmp_path):
    assert "midair" in blocks(tmp_path, column(extra_top=square(180, 180, 12, e0=50)))


def test_midair_island_on_support_passes(tmp_path):
    g = column(extra_top=square(180, 180, 12, e0=50), support_under_top=True)
    assert "midair" not in blocks(tmp_path, g)


def test_anchored_bridge_passes(tmp_path):
    out = ["M104 S210", "M140 S60", "G28", "BED_MESH_CALIBRATE"]
    for i, z in enumerate((0.28, 0.52, 0.76)):
        out += [";LAYER_CHANGE", f"G1 Z{z}"]
        out += square(100, 100, 20, e0=10 * i + 1) + square(160, 100, 20, e0=10 * i + 5)
        if i == 2:
            out += ["G1 X120 Y110 E40", "G1 X160 Y110 E41"]
    assert "midair" not in blocks(tmp_path, "\n".join(out) + "\n")


def test_steep_shell_warns(tmp_path):
    assert "midair" in warns(tmp_path, column(shift_top=25))


def test_compact_gcode_is_read(tmp_path):
    compact = HEALTHY.replace("G1 ", "G1").replace("M104 ", "M104").replace("M140 ", "M140")
    assert not blocks(tmp_path, compact) and not warns(tmp_path, compact)
    assert "first-z" in blocks(tmp_path, compact.replace("G1Z0.28", "G1Z0.0"))


def test_off_bed_limits_follow_their_axis(tmp_path):
    p = tmp_path / "t.gcode"
    p.write_text("G28\n;LAYER_CHANGE\nG1 Z0.3\nG1 X100 Y240 E1\nG1 X130 Y240 E2\n")
    over = [f for f in preflight(p, KLIPPER).findings if f.check == "off-bed"]
    assert over and over[0].data["axis"] == "Y" and over[0].data["limit"] == 220


def test_unmarked_file_counts_islands_on_the_first_layer_only(tmp_path):
    g = "G28\nG1 Z0.3\n" + "\n".join(square(100, 100, 30)) + "\nG1 Z0.6\n" + \
        "\n".join(square(100, 100, 30)) + "\n" + "\n".join(square(160, 100, 30)) + "\n"
    assert "fusion" not in blocks(tmp_path, g, parts=1)


def test_a_small_part_beside_a_large_one_blocks(tmp_path):
    big = square(100, 100, 30)
    small = square(150, 100, 6, e0=10)
    g = "M104 S210\nM140 S60\nG28\n;LAYER_CHANGE\nG1 Z0.28\n" + "\n".join(big + small) + "\n"
    assert "island-footprint" in blocks(tmp_path, g, parts=2)
    assert "first-layer" not in blocks(tmp_path, g, parts=2)


def test_a_brimmed_small_part_passes(tmp_path):
    brimmed = square(150, 100, 17, e0=10)
    g = "M104 S210\nM140 S60\nG28\n;LAYER_CHANGE\nG1 Z0.28\n" + "\n".join(
        square(100, 100, 30) + brimmed) + "\n"
    assert "island-footprint" not in blocks(tmp_path, g, parts=2)
