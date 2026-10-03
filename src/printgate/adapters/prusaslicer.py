"""Slice through the PrusaSlicer command line (PrusaSlicer and its forks share the flags)."""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


class PrusaSlicer:
    def __init__(self, config: Path, center: tuple[float, float] | None = None):
        self.config = Path(config)
        self.center = center
        self.cmd = shlex.split(os.environ.get("PRINTGATE_PRUSASLICER", "prusa-slicer"))

    def slice(self, stl: Path, gcode: Path) -> Path:
        args = [*self.cmd, "--load", str(self.config), "--export-gcode", str(stl), "--output", str(gcode)]
        if self.center:
            args[1:1] = ["--center", "{},{}".format(*self.center)]
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=900)
        except FileNotFoundError:
            raise RuntimeError(f"PrusaSlicer not found as {self.cmd[0]!r}; install it or set "
                               "PRINTGATE_PRUSASLICER")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"slicing {stl.name} took over 900 s")
        if r.returncode or not gcode.exists():
            raise RuntimeError(f"slicing {stl.name} failed:\n{(r.stderr + r.stdout)[-800:]}")
        return gcode
