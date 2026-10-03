"""Run OpenSCAD: render a model with parameter overrides, to a mesh or an image."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ENV = "PRINTGATE_OPENSCAD"


def command() -> list[str]:
    return shlex.split(os.environ.get(ENV, "openscad"))


def available() -> bool:
    return shutil.which(command()[0]) is not None


def define(name: str, value) -> list[str]:
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, str):
        v = '"' + value.replace('"', '\\"') + '"'
    else:
        v = repr(value)
    return ["-D", f"{name}={v}"]


@dataclass
class Render:
    out: Path
    ok: bool
    log: str

    @property
    def failed_assert(self) -> bool:
        return "Assertion" in self.log and not self.ok


def run(scad: Path, out: Path, defines: dict | None = None, extra=(), timeout=600) -> Render:
    args = [a for k, v in (defines or {}).items() for a in define(k, v)]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    try:
        r = subprocess.run([*command(), "-o", str(out), *extra, *args, str(scad)],
                           capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError(f"OpenSCAD not found as {command()[0]!r}; install it or set {ENV}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"OpenSCAD took over {timeout} s on {scad}")
    return Render(out, out.exists() and out.stat().st_size > 0, r.stderr + r.stdout)


def image(src: Path, out: Path, rotation=(55, 0, 25), defines: dict | None = None) -> Render:
    """A full render (not preview) so cut faces and colours come out right."""
    if src.suffix.lower() == ".stl":
        wrapper = out.with_suffix(".scad")
        wrapper.write_text(f'import("{src.resolve()}");\n')
        src = wrapper
    cam = "0,0,0,{},{},{},0".format(*rotation)
    try:
        return run(src, out, defines, ["--render", "--imgsize=800,600", "--autocenter",
                                       "--viewall", "--colorscheme=Tomorrow", f"--camera={cam}"])
    finally:
        if src.suffix == ".scad" and src.parent == out.parent:
            src.unlink(missing_ok=True)


def version() -> str:
    r = subprocess.run([*command(), "--version"], capture_output=True, text=True)
    return (r.stderr or r.stdout).strip()
