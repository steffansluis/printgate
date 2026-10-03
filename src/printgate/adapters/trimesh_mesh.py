"""Mesh metrics through trimesh."""
from __future__ import annotations

from pathlib import Path

# A face pointing down more steeply than 45 deg from vertical needs support (cos 45 = 0.7071);
# the margin keeps exact 45 deg chamfers, which print fine, out of the count.
OVERHANG_NZ = -0.72


class TrimeshAnalyzer:
    def analyze(self, stl: Path) -> dict[str, float | str]:
        import numpy as np
        import trimesh

        m = trimesh.load_mesh(stl, process=True)
        n = m.face_normals
        zmin = m.bounds[0][2]
        on_bed = (n[:, 2] < -0.99) & (np.abs(m.triangles[:, :, 2] - zmin).max(axis=1) < 0.01)
        overhang = (n[:, 2] < OVERHANG_NZ) & ~on_bed
        size = m.extents
        return {
            "Size X×Y×Z (mm)": "{:.1f} × {:.1f} × {:.1f}".format(*size),
            "Height (mm)": float(size[2]),
            "Volume (cm³)": float(m.volume) / 1000,
            "Surface area (cm²)": float(m.area) / 100,
            "First-layer contact (mm²)": float(m.area_faces[on_bed].sum()),
            "Overhang >45° (mm²)": float(m.area_faces[overhang].sum()),
            "Watertight": "yes" if m.is_watertight else "no",
        }
