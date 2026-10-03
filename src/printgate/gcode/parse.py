"""Read G-code into a toolpath: layers of segments, plus the facts the checks need."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

# Layer-change comments from PrusaSlicer, OrcaSlicer and Cura. Delimiting layers by them keeps a
# prime line printed before the first layer from passing for a tiny first layer.
LAYER_MARK = re.compile(r"^;\s*(LAYER:\d|LAYER_CHANGE|AFTER_LAYER_CHANGE)")
WORD = re.compile(r"([A-Z])(-?\d*\.?\d+)")
# Slicer estimates: PrusaSlicer and OrcaSlicer write the first two, Cura the last.
EST_TIME = re.compile(r"^; estimated printing time \(normal mode\) = (.+)$", re.M)
EST_CM3 = re.compile(r"^; filament used \[cm3\] = ([\d.]+)", re.M)
EST_G = re.compile(r"^; total filament used \[g\] = ([\d.]+)", re.M)
CURA_TIME = re.compile(r"^;TIME:(\d+)", re.M)
MOVE = re.compile(r"(G[01])(?![0-9])", re.I)
DURATION = re.compile(r"(\d+)\s*([dhms])")


@dataclass
class Segment:
    x0: float
    y0: float
    x1: float
    y1: float
    support: bool


@dataclass
class Layer:
    z: float
    segments: list[Segment] = field(default_factory=list)   # extruding moves only
    seconds: float = 0.0

    def bbox_area(self) -> float:
        xs = [s.x1 for s in self.segments]
        ys = [s.y1 for s in self.segments]
        if len(xs) < 2:
            return 0.0
        return (max(xs) - min(xs)) * (max(ys) - min(ys))


@dataclass
class Toolpath:
    text: str
    layers: list[Layer]
    marked: bool                       # layers came from slicer comments, not Z grouping
    first_extrude_z: float | None
    peak_fan: float                    # highest M106 S after the first two layers
    max_xyz: dict[str, tuple[float, str]]   # axis -> (largest value, the line commanding it)
    negative_z: str | None
    support_z: list[float]
    max_z: float
    estimates: dict[str, float] = field(default_factory=dict)   # seconds, filament_cm3


def estimates(text: str) -> dict[str, float]:
    out = {}
    if m := EST_TIME.search(text):
        unit = {"d": 86400, "h": 3600, "m": 60, "s": 1}
        out["seconds"] = float(sum(int(n) * unit[u] for n, u in DURATION.findall(m[1])))
    elif m := CURA_TIME.search(text):
        out["seconds"] = float(m[1])
    if m := EST_CM3.search(text):
        out["filament_cm3"] = float(m[1])
    if (m := EST_G.search(text)) and float(m[1]) > 0:    # 0 when the config sets no density
        out["filament_g"] = float(m[1])
    return out


def _words(line: str) -> dict[str, float]:
    code = line.split(";", 1)[0].upper()
    return {k: float(v) for k, v in WORD.findall(code)}


def read(path: Path | str) -> Toolpath:
    text = Path(path).read_text(errors="replace")
    lines = text.splitlines()
    marked = any(LAYER_MARK.match(line) for line in lines)

    x = y = z = 0.0
    feed = 1800.0
    support = False
    layers: list[Layer] = []
    z_set = False
    by_z: dict[float, Layer] = {}
    first_extrude_z = None
    peak_fan = 0.0
    max_xyz = {"X": (-math.inf, ""), "Y": (-math.inf, ""), "Z": (-math.inf, "")}
    negative_z = None
    support_z: list[float] = []
    max_z = 0.0

    for line in lines:
        stripped = line.lstrip()
        if marked and LAYER_MARK.match(line):
            layers.append(Layer(z))
            z_set = False
            continue
        if stripped.startswith(";TYPE:"):
            support = "support" in stripped.lower()
            continue
        if stripped.startswith(";"):
            continue
        if stripped.startswith("M106"):
            s = _words(stripped).get("S")
            if s is not None and len(layers) >= 3:   # the first layers usually run the fan off
                peak_fan = max(peak_fan, s)
            continue
        # Slicers may omit the spaces ("G1X10Y10E1"); G10 and G11 are not moves.
        if not (m := MOVE.match(stripped)):
            continue
        cmd = m[1].upper()

        w = _words(stripped)
        feed = w.get("F", feed)
        for axis in "XYZ":
            if axis in w and w[axis] > max_xyz[axis][0]:
                max_xyz[axis] = (w[axis], stripped)
        if "Z" in w:
            z = round(w["Z"], 2)
            max_z = max(max_z, z)
            if w["Z"] < 0 and negative_z is None:
                negative_z = stripped
            # Only the first Z after a marker is the layer's height; an end-of-print lift is not.
            if layers and not z_set:
                layers[-1].z = z
                z_set = True
        nx, ny = w.get("X", x), w.get("Y", y)
        extruding = cmd == "G1" and "X" in w and "Y" in w and "E" in w
        if extruding and first_extrude_z is None:
            first_extrude_z = z
        if support and cmd == "G1" and "X" in w and "E" in w:
            support_z.append(z)

        layer = None
        if marked:
            layer = layers[-1] if layers else None    # before the first marker: a prime line
        elif extruding:
            layer = by_z.setdefault(z, Layer(z))
        if layer is not None:
            if cmd == "G1" and "X" in w and "Y" in w:
                layer.seconds += math.hypot(nx - x, ny - y) / (feed / 60.0)
            if extruding:
                layer.segments.append(Segment(x, y, nx, ny, support))
        x, y = nx, ny

    if not marked:
        layers = [by_z[k] for k in sorted(by_z)]
    return Toolpath(text, [l for l in layers if l.segments], marked, first_extrude_z, peak_fan,
                    {k: v for k, v in max_xyz.items() if v[1]}, negative_z, support_z, max_z,
                    estimates(text))


def raster(segments: list[Segment], cell: float) -> set[tuple[int, int]]:
    """Grid cells the extrusions cross, sampled finely enough that one part stays connected."""
    cells = set()
    for s in segments:
        dx, dy = s.x1 - s.x0, s.y1 - s.y0
        n = max(1, int(math.hypot(dx, dy) / (cell * 0.4)))
        for i in range(n + 1):
            t = i / n
            cells.add((round((s.x0 + dx * t) / cell), round((s.y0 + dy * t) / cell)))
    return cells


def components(cells: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    """8-connected components of a cell set."""
    remaining, out = set(cells), []
    while remaining:
        comp, stack = set(), [remaining.pop()]
        while stack:
            c = stack.pop()
            comp.add(c)
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    nb = (c[0] + ox, c[1] + oy)
                    if nb in remaining:
                        remaining.discard(nb)
                        stack.append(nb)
        out.append(comp)
    return out


def dilate(cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    return {(x + ox, y + oy) for x, y in cells for ox in (-1, 0, 1) for oy in (-1, 0, 1)}
