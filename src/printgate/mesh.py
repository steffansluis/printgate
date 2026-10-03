"""Checks on mesh metrics, whichever analyzer produced them."""
from __future__ import annotations

from .contract import Finding, Severity
from .profile import Profile

SUPPORT_MM2 = 25.0   # less than this is a few stray facets, not a part that needs support


def fits(metrics: dict, profile: Profile) -> Finding | None:
    size = [metrics.get(k) for k in ("Width X (mm)", "Depth Y (mm)", "Height Z (mm)")]
    if all(isinstance(v, float) for v in size) and \
            any(v > lim for v, lim in zip(size, profile.bed_max)):
        dims = " × ".join(f"{v:.0f}" for v in size)
        bed = " × ".join(f"{v:.0f}" for v in profile.bed_max)
        return Finding("bed-fit", Severity.BLOCK, f"{dims} mm does not fit the {bed} mm build volume")
    return None


def checks(metrics: dict, profile: Profile) -> list[Finding]:
    out = []
    contact = metrics.get("First-layer contact (mm²)")
    if isinstance(contact, float) and contact < profile.min_first_layer_mm2:
        out.append(Finding("first-layer", Severity.WARN, f"first-layer contact is {contact:.0f} mm² "
                           f"(< {profile.min_first_layer_mm2:.0f}): use a brim or reorient"))
    overhang = metrics.get("Overhang >45° (mm²)")
    if isinstance(overhang, float) and overhang > SUPPORT_MM2:
        out.append(Finding("overhang", Severity.WARN, f"{overhang:.0f} mm² overhangs past 45°: "
                           f"needs support in this orientation"))
    wall = metrics.get("Thinnest wall (mm)")
    if isinstance(wall, float) and wall < profile.min_wall_mm:
        out.append(Finding("thin-wall", Severity.WARN, f"walls down to {wall:.2f} mm "
                           f"(< {profile.min_wall_mm} mm, two extrusion widths) may not print"))
    bodies = metrics.get("Bodies")
    if isinstance(bodies, int) and bodies > 1:
        out.append(Finding("bodies", Severity.WARN, f"{bodies} separate bodies: intended, or a "
                           "part that does not touch the rest?"))
    if metrics.get("Watertight") == "no":
        out.append(Finding("watertight", Severity.BLOCK, "mesh is not watertight: slicers may "
                           "fill or drop parts of it"))
    return out
