"""Checks on mesh metrics, whichever analyzer produced them."""
from __future__ import annotations

from .contract import Finding, Severity
from .profile import Profile

SUPPORT_MM2 = 25.0   # less than this is a few stray facets, not a part that needs support


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
    if metrics.get("Watertight") == "no":
        out.append(Finding("watertight", Severity.BLOCK, "mesh is not watertight: slicers may "
                           "fill or drop parts of it"))
    return out
