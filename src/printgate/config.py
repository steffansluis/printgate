"""Project configuration: which printers exist and how to slice for them.

Found the way coverage or pytest find theirs, first match wins:
  1. an explicit path (`--config`), or the PRINTGATE_CONFIG environment variable
  2. `printgate.toml` in the working directory
  3. `[tool.printgate]` in `pyproject.toml` in the working directory

    [printers.my-printer]
    firmware = "klipper"                      # any Profile field
    bed_max = [220, 220, 280]
    slicer = "prusaslicer"                    # an adapter name
    slicer_config = "profiles/pla.ini"        # relative to the config file
    center = [110, 110]
    filament_density = 1.24                   # g/cm³, when the slicer reports no grams itself

    [review]
    context = { mode = "assembly" }           # an extra view, for models that declare `mode`

    [review.views]                            # more named views, e.g. the variants of a design
    plate = { mode = "plate" }
    closed = { mode = "disk", cord_slot = false }

PRINTGATE_PRINTERS="a,b" narrows the printers to those names, e.g. for one CI job per printer.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from .profile import Profile

PRINTER_KEYS = {"slicer", "slicer_config", "center", "filament_density"}


@dataclass(frozen=True)
class Printer:
    name: str
    profile: Profile = field(default_factory=Profile)
    slicer: str | None = None
    slicer_config: Path | None = None
    center: tuple[float, float] | None = None
    filament_density: float = 1.24      # PLA


@dataclass(frozen=True)
class Config:
    printers: tuple[Printer, ...] = ()
    source: Path | None = None
    context: dict = field(default_factory=dict)
    views: dict = field(default_factory=dict)

    def printer(self, name: str) -> Printer:
        for p in self.printers:
            if p.name == name:
                return p
        known = ", ".join(p.name for p in self.printers) or "none configured"
        raise KeyError(f"no printer {name!r}; known: {known}")


def _printer(name: str, data: dict, base: Path) -> Printer:
    profile_keys = {f.name for f in fields(Profile)}
    unknown = set(data) - profile_keys - PRINTER_KEYS
    if unknown:
        raise ValueError(f"printer {name!r}: unknown keys {', '.join(sorted(unknown))}")
    profile = Profile.from_dict({k: v for k, v in data.items() if k in profile_keys})
    cfg = data.get("slicer_config")
    return Printer(name, profile, data.get("slicer"), base / cfg if cfg else None,
                   tuple(data["center"]) if "center" in data else None,
                   float(data.get("filament_density", 1.24)))


def load(path: Path | str | None = None, cwd: Path | None = None) -> Config:
    cwd = cwd or Path.cwd()
    explicit = path or os.environ.get("PRINTGATE_CONFIG")
    if explicit:
        source = Path(explicit)
        data = tomllib.loads(source.read_text())
    elif (cwd / "printgate.toml").exists():
        source = cwd / "printgate.toml"
        data = tomllib.loads(source.read_text())
    elif (cwd / "pyproject.toml").exists() and \
            "printgate" in (pp := tomllib.loads((cwd / "pyproject.toml").read_text())).get("tool", {}):
        source, data = cwd / "pyproject.toml", pp["tool"]["printgate"]
    else:
        return Config()

    unknown = set(data) - {"printers", "review"}
    if unknown:
        raise ValueError(f"{source}: unknown keys {', '.join(sorted(unknown))}")
    review = data.get("review", {})
    if set(review) - {"context", "views"}:
        raise ValueError(f"{source}: unknown [review] keys "
                         f"{', '.join(sorted(set(review) - {'context', 'views'}))}")
    printers = [_printer(n, d, source.parent) for n, d in data.get("printers", {}).items()]
    if wanted := os.environ.get("PRINTGATE_PRINTERS"):
        names = [n.strip() for n in wanted.split(",") if n.strip()]
        config = Config(tuple(printers), source)
        printers = [config.printer(n) for n in names]
    return Config(tuple(printers), source, dict(review.get("context", {})),
                  {k: dict(v) for k, v in review.get("views", {}).items()})
