"""Mesh metrics through trimesh."""
from __future__ import annotations

from pathlib import Path

# A face pointing down more steeply than 45 deg from vertical needs support (cos 45 = 0.7071);
# the margin keeps exact 45 deg chamfers, which print fine, out of the count.
OVERHANG_NZ = -0.72


def _bodies(m) -> int:
    parent = list(range(len(m.faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in m.face_adjacency:
        parent[find(a)] = find(b)
    return len({find(i) for i in range(len(parent))})


SAMPLES = 1500   # rays; without embree each costs about a millisecond on a small part


def _thinnest_wall(m) -> float:
    """Area-weighted 1st percentile of the inward ray thickness. The minimum alone is a chamfer
    tip or a knife edge, not a wall. Large meshes are sampled, with a fixed seed so the same
    mesh always reports the same number."""
    import numpy as np
    import trimesh

    faces = np.arange(len(m.faces))
    if len(faces) > SAMPLES:
        rng = np.random.default_rng(0)
        faces = np.sort(rng.choice(faces, SAMPLES, replace=False, p=m.area_faces / m.area))
    t = trimesh.proximity.thickness(m, m.triangles_center[faces], exterior=False,
                                    normals=m.face_normals[faces], method="ray")
    ok = np.isfinite(t)
    t, w = t[ok], m.area_faces[faces][ok]
    order = np.argsort(t)
    cum = np.cumsum(w[order]) / w.sum()
    return float(t[order][np.searchsorted(cum, 0.01)])


class TrimeshAnalyzer:
    def analyze(self, stl: Path) -> dict[str, float | str]:
        import numpy as np
        import trimesh

        m = trimesh.load_mesh(stl, process=True)
        n = m.face_normals
        zmin = m.bounds[0][2]
        on_bed = (n[:, 2] < -0.99) & (np.abs(m.triangles[:, :, 2] - zmin).max(axis=1) < 0.01)
        overhang = (n[:, 2] < OVERHANG_NZ) & ~on_bed
        x, y, z = (float(v) for v in m.extents)
        return {
            "Width X (mm)": x,
            "Depth Y (mm)": y,
            "Height Z (mm)": z,
            "Volume (cm³)": float(m.volume) / 1000,
            "Surface area (cm²)": float(m.area) / 100,
            "First-layer contact (mm²)": float(m.area_faces[on_bed].sum()),
            "Overhang >45° (mm²)": float(m.area_faces[overhang].sum()),
            "Thinnest wall (mm)": _thinnest_wall(m),
            "Bodies": _bodies(m),
            "Watertight": "yes" if m.is_watertight else "no",
        }
