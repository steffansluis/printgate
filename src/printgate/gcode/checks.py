"""Static checks on a toolpath. Each is a pure function of (toolpath, profile, expected parts)."""
from __future__ import annotations

import re
from typing import Callable

from ..contract import Finding, Severity
from ..profile import DIALECTS, Profile
from .parse import Toolpath, components, dilate, raster

Check = Callable[[Toolpath, Profile, "int | None"], list[Finding]]
B, W, I = Severity.BLOCK, Severity.WARN, Severity.INFO
EARLY_LAYERS = 12


def firmware(tp: Toolpath, p: Profile, _parts) -> list[Finding]:
    out = []
    for sev, codes in ((B, DIALECTS[p.firmware]["block"]), (W, DIALECTS[p.firmware]["warn"])):
        found = sorted({c for c in codes if re.search(rf"^\s*{c}\b", tp.text, re.M)})
        if found:
            verb = "aborts the print" if sev is B else "is tolerated but better removed"
            out.append(Finding("firmware", sev, f"{', '.join(found)} on {p.firmware}: {verb}",
                               {"codes": found}))
    return out


def temperatures(tp: Toolpath, _p, _parts) -> list[Finding]:
    out = []
    if not re.search(r"^M10[49]\s*S(1[6-9]\d|2\d\d)", tp.text, re.M):
        out.append(Finding("temperatures", W, "no nozzle temperature of 160 °C or more is set"))
    if not re.search(r"^M1[49]0\s*S[3-9]\d", tp.text, re.M):
        out.append(Finding("temperatures", W, "no bed temperature is set"))
    return out


def z_safety(tp: Toolpath, p: Profile, _parts) -> list[Finding]:
    """The file can't know the live Z offset, but it must never itself drive the nozzle down."""
    out = []
    if not re.search(r"^\s*G28\b", tp.text, re.M):
        out.append(Finding("homing", B, "no G28 before printing: the Z origin is undefined"))
    if p.require_leveling and not re.search(r"BED_MESH_CALIBRATE|BED_MESH_PROFILE|^\s*G29\b",
                                            tp.text, re.M):
        out.append(Finding("leveling", W, "no bed mesh is probed or loaded"))
    if tp.negative_z:
        out.append(Finding("negative-z", B, f"move below the bed: {tp.negative_z[:48]!r}"))
    if tp.first_extrude_z is not None and tp.first_extrude_z < p.min_first_z:
        out.append(Finding("first-z", B, f"first extrusion at Z={tp.first_extrude_z} is below "
                                         f"{p.min_first_z} mm: the nozzle drags on the plate",
                           {"z": tp.first_extrude_z}))
    return out


def off_bed(tp: Toolpath, p: Profile, _parts) -> list[Finding]:
    limits = dict(zip("XYZ", p.bed_max))
    over = [(axis, v, line, limits[axis]) for axis, (v, line) in tp.max_xyz.items()
            if v > limits[axis] + 0.05]
    if not over:
        return []
    axis, v, line, lim = max(over, key=lambda o: o[1] - o[3])
    return [Finding("off-bed", B, f"{axis}={v:.2f} passes the {lim:.0f} mm limit by {v - lim:.2f} mm "
                                  f"({line[:48]!r}); re-centre or shrink the plate",
                    {"axis": axis, "value": v, "limit": lim})]


def support(tp: Toolpath, _p, _parts) -> list[Finding]:
    """Support low on a part usually sits on a mating face, where it won't release cleanly."""
    if not tp.support_z:
        return []
    third = tp.max_z / 3.0
    low = [z for z in tp.support_z if z <= third]
    out = [Finding("support", I, f"support: {len(tp.support_z)} moves, "
                                 f"Z {min(tp.support_z):.1f}..{max(tp.support_z):.1f}")]
    if low:
        out.append(Finding("support", B, f"support in the bottom third (Z ≤ {third:.1f}, {len(low)} "
                                         f"moves) is likely on a mating face; reorient or bridge it",
                           {"moves": len(low)}))
    else:
        out.append(Finding("support", W, "support in the upper part only: confirm it touches no fit face"))
    return out


def midair(tp: Toolpath, p: Profile, _parts) -> list[Finding]:
    """An island with nothing below it extrudes into air. Slicer overhang tags can't tell this
    apart from a good bridge, so compare each layer's raster with the dilated layer below."""
    if not tp.marked or len(tp.layers) < 2:
        return []
    floating, steep = [], []
    below = raster(tp.layers[0].segments, p.raster_mm)
    for layer in tp.layers[1:]:
        cells = raster(layer.segments, p.raster_mm)
        held = dilate(below)
        unheld = sum(1 for c in cells if c not in held)
        if len(cells) >= 50 and unheld / len(cells) >= 0.60:
            steep.append((layer.z, unheld / len(cells)))
        floating += [(layer.z, len(c)) for c in components(cells) if len(c) >= 3 and not c & held]
        below = cells
    if floating:
        where = ", ".join(f"Z={z} ({n} cells)" for z, n in floating[:4])
        return [Finding("midair", B, f"geometry starts in mid-air at {where}; lay the part on a "
                                     f"larger face or support it", {"islands": floating})]
    if steep:
        z, frac = max(steep, key=lambda s: s[1])
        return [Finding("midair", W, f"{len(steep)} layer(s) hang ≥60% past the layer below "
                                     f"(worst Z={z}, {frac:.0%})")]
    return []


def islands(tp: Toolpath, p: Profile) -> int:
    return len(components(raster(tp.layers[0].segments, p.raster_mm))) if tp.layers else 0


def shape(tp: Toolpath, p: Profile, parts) -> list[Finding]:
    areas = [(l.z, l.bbox_area()) for l in tp.layers if len(l.segments) >= 2]
    if not areas:
        return [Finding("shape", W, "no layer geometry could be read; shape checks skipped")]
    base, top = areas[0][1], max(a for _, a in areas)
    n = islands(tp, p)
    out = [Finding("shape", I, f"{len(areas)} layers, first layer {base:.0f} mm², largest "
                               f"{top:.0f} mm², height {areas[-1][0]} mm, {n} island(s)",
                   {"first_layer_mm2": base, "max_layer_mm2": top, "islands": n})]
    if base < p.min_first_layer_mm2:
        out.append(Finding("first-layer", B, f"first layer covers {base:.0f} mm² (< "
                                             f"{p.min_first_layer_mm2:.0f}): reorient or add a brim"))
    for (_, a0), (z1, a1) in zip(areas, areas[1:EARLY_LAYERS]):
        if a0 > 0 and a1 / a0 >= p.cantilever_jump and a1 > p.min_first_layer_mm2:
            out.append(Finding("cantilever", B, f"cross-section grows {a0:.0f}→{a1:.0f} mm² "
                                                f"({a1 / a0:.1f}×) at Z={z1}: a large layer on a small base"))
            break
    if base > 0 and top / base >= p.top_heavy_ratio:
        out.append(Finding("top-heavy", W, f"largest layer is {top / base:.1f}× the first: "
                                           f"put the largest face on the bed"))
    # The bounding box above spans the whole plate, so a small part beside a large one passes it;
    # each island must hold the bed on its own footprint.
    for comp in components(raster(tp.layers[0].segments, p.raster_mm)):
        xs, ys = [c[0] for c in comp], [c[1] for c in comp]
        area = (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1) * p.raster_mm ** 2
        if area < p.min_island_mm2:
            out.append(Finding("island-footprint", B, f"a part covers only {area:.0f} mm² of the first "
                               f"layer (< {p.min_island_mm2:.0f}): brim it, or print it with one",
                               {"area_mm2": area}))
            break
    if parts is not None and n < parts:
        out.append(Finding("fusion", B, f"expected {parts} parts but the first layer has {n} "
                                        f"island(s): footprints or brims have merged"))
    return out


def warp(tp: Toolpath, p: Profile, _parts) -> list[Finding]:
    """A small part whose layers finish in seconds lays each one on a still-soft layer and curls.
    Slowing down can't fix it once the minimum speed binds; a second copy on the plate can."""
    timed = [l.seconds for l in tp.layers if l.seconds > 0.05]
    if not tp.marked or len(timed) < 6:
        return []
    fast = sum(1 for t in timed if t < p.fast_layer_s)
    if fast < 0.5 * len(timed):
        return []
    small = tp.layers[0].bbox_area() < p.warp_small_mm2
    if islands(tp, p) < 2 and small:
        return [Finding("warp", B, f"{fast}/{len(timed)} layers finish under {p.fast_layer_s:.0f} s "
                                   f"on a single small part: print two or more copies apart")]
    if tp.peak_fan < 0.9 * 255:
        return [Finding("warp", W, f"{fast}/{len(timed)} fast layers with the fan peaking at "
                                   f"{tp.peak_fan:.0f}/255: run it at full")]
    return []


CHECKS: list[Check] = [firmware, temperatures, z_safety, off_bed, warp, support, midair, shape]


def run(tp: Toolpath, profile: Profile, parts: int | None = None) -> list[Finding]:
    return [f for check in CHECKS for f in check(tp, profile, parts)]
