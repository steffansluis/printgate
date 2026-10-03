import subprocess

from printgate.adapters.prusaslicer import PrusaSlicer


def test_options_follow_a_wrapped_command(tmp_path, monkeypatch):
    seen = []

    def run(args, **kw):
        seen.append(args)
        (tmp_path / "p.gcode").write_text("")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setenv("PRINTGATE_PRUSASLICER", "xvfb-run -a prusa-slicer")
    monkeypatch.setattr(subprocess, "run", run)
    PrusaSlicer(tmp_path / "c.ini", (110, 110)).slice(tmp_path / "p.stl", tmp_path / "p.gcode")
    assert seen[0][:5] == ["xvfb-run", "-a", "prusa-slicer", "--center", "110,110"]
