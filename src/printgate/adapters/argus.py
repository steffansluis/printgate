"""Geometric diff through argus-diff (https://github.com/mikelmyers/argus-diff).

argus-diff matches bodies and faces on STEP; on meshes it reports the body-level deltas.
Its own text summary is attached as-is rather than re-parsed.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


class ArgusDiffer:
    def __init__(self, density_g_cm3: float = 1.27):
        self.density = density_g_cm3
        self.cmd = shlex.split(os.environ.get("PRINTGATE_ARGUS", "argus"))

    def diff(self, old: Path, new: Path) -> str:
        try:
            r = subprocess.run([*self.cmd, "diff", str(old), str(new), "--density", str(self.density)],
                               capture_output=True, text=True, timeout=600)
        except FileNotFoundError:
            raise RuntimeError(f"argus-diff not found as {self.cmd[0]!r}; pip install argus-diff "
                               "or set PRINTGATE_ARGUS")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"argus-diff took over 600 s on {new.name}")
        if r.returncode == 2:
            raise RuntimeError(f"argus-diff could not load the meshes:\n{r.stderr[-800:]}")
        return r.stdout.strip()
