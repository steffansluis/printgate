import json

from printgate.cli import main

GOOD = "M104 S210\nM140 S60\nG28\n;LAYER_CHANGE\nG1 Z0.28\n" + \
       "G1 X100 Y100 E1\nG1 X130 Y100 E2\nG1 X130 Y130 E3\nG1 X100 Y130 E4\n"


def test_gcode_exit_codes(tmp_path):
    good, bad = tmp_path / "good.gcode", tmp_path / "bad.gcode"
    good.write_text(GOOD)
    bad.write_text(GOOD.replace("G28\n", ""))
    assert main(["gcode", str(good)]) == 0
    assert main(["gcode", str(bad)]) == 1
    assert main(["gcode", str(good), "--format", "nonesuch"]) == 2


def test_profile_and_json(tmp_path, capsys):
    g = tmp_path / "g.gcode"
    g.write_text("G80\n" + GOOD)
    prof = tmp_path / "p.toml"
    prof.write_text('firmware = "klipper"\nbed_max = [220, 220, 280]\n')
    assert main(["gcode", str(g), "--profile", str(prof), "--format", "json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out[0]["blocked"] and any(f["check"] == "firmware" for f in out[0]["findings"])


def test_unknown_profile_key_is_a_usage_error(tmp_path):
    prof = tmp_path / "p.toml"
    prof.write_text("bed_size = 1\n")
    assert main(["gcode", "x.gcode", "--profile", str(prof)]) == 2


def test_mistyped_profile_value_is_a_usage_error(tmp_path):
    prof = tmp_path / "p.toml"
    prof.write_text('min_first_z = "0.1"\n')
    assert main(["gcode", "x.gcode", "--profile", str(prof)]) == 2


def test_missing_openscad_names_the_setting(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PRINTGATE_OPENSCAD", "/nonexistent/openscad")
    scad = tmp_path / "m.scad"
    scad.write_text("cube(1);\n")
    assert main(["review", str(scad), "--out", str(tmp_path / "o")]) == 2
    assert "PRINTGATE_OPENSCAD" in capsys.readouterr().err
