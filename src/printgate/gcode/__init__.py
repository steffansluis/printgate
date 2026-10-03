"""G-code preflight: read a sliced file and judge it against a printer profile."""
from __future__ import annotations

from pathlib import Path

from ..contract import Report
from ..profile import Profile
from . import checks
from .parse import read


def preflight(path: Path | str, profile: Profile | None = None, parts: int | None = None,
              filament_density: float | None = None) -> Report:
    tp = read(path)
    metrics: dict[str, float | str] = {}
    if "seconds" in tp.estimates:
        metrics["Print time (min)"] = tp.estimates["seconds"] / 60
    if "filament_cm3" in tp.estimates:
        metrics["Filament (cm³)"] = tp.estimates["filament_cm3"]
        if filament_density:
            metrics["Filament (g)"] = tp.estimates["filament_cm3"] * filament_density
    return Report(subject=str(path), findings=checks.run(tp, profile or Profile(), parts),
                  metrics=metrics)
