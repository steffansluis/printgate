"""A printer profile: the limits and thresholds the G-code checks judge against."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields, replace
from pathlib import Path

# Commands each firmware rejects outright (block) or accepts with a caveat (warn).
# Only entries someone has seen fail belong here; an empty dialect checks nothing.
DIALECTS = {
    "klipper": {"block": ["M862", "G80"], "warn": ["M205"]},
    "generic": {"block": [], "warn": []},
}


@dataclass(frozen=True)
class Profile:
    bed_max: tuple[float, float, float] = (220.0, 220.0, 250.0)
    firmware: str = "generic"
    min_first_layer_mm2: float = 500.0    # below this a part detaches more often than not
    cantilever_jump: float = 2.5          # layer area over the one below, within the first 12
    top_heavy_ratio: float = 3.0          # largest layer area over the first layer's
    min_first_z: float = 0.1              # a first extrusion lower than this drags on the plate
    min_wall_mm: float = 0.9              # two extrusion widths at a 0.4 mm nozzle
    require_leveling: bool = False        # warn when no mesh is probed or loaded
    fast_layer_s: float = 10.0
    warp_small_mm2: float = 1500.0        # warp only blocks parts with a smaller footprint
    raster_mm: float = 1.0                # grid for island and mid-air detection

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown profile keys: {', '.join(sorted(unknown))}")
        data = dict(data)
        defaults = cls()
        for key, value in data.items():
            want = type(getattr(defaults, key))
            if key == "bed_max":
                ok = isinstance(value, list) and len(value) == 3 and \
                    all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
                value = tuple(float(v) for v in value) if ok else value
            elif want is float:
                ok = isinstance(value, (int, float)) and not isinstance(value, bool)
                value = float(value) if ok else value
            else:
                ok = isinstance(value, want)
            if not ok:
                raise ValueError(f"profile key {key!r}: expected {want.__name__}"
                                 f"{' of three numbers' if key == 'bed_max' else ''}, got {value!r}")
            data[key] = value
        profile = replace(defaults, **data)
        if profile.firmware not in DIALECTS:
            raise ValueError(f"unknown firmware {profile.firmware!r}; known: {', '.join(DIALECTS)}")
        return profile

    @classmethod
    def load(cls, path: Path) -> "Profile":
        return cls.from_dict(tomllib.loads(Path(path).read_text()))
