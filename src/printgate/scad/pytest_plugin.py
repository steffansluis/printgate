"""pytest fixture for models whose asserts encode their design rules.

    def test_bracket_rejects_a_slot_too_wide(openscad):
        openscad.fails("bracket.scad", "slot wider than the rail", slot_w=25)

A model that guards itself with assert() is only as good as the proof that the assert fires;
`fails` is that proof, `renders` is the matching proof that good parameters still render.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from . import openscad as osc


class OpenSCAD:
    def __init__(self, tmp: Path):
        self.tmp = tmp

    def render(self, scad, **defines) -> osc.Render:
        return osc.run(Path(scad), self.tmp / f"{Path(scad).stem}.stl", defines)

    def renders(self, scad, **defines) -> osc.Render:
        r = self.render(scad, **defines)
        assert r.ok, f"{scad} {defines} did not render:\n{r.log[-800:]}"
        return r

    def fails(self, scad, match: str, **defines) -> osc.Render:
        r = self.render(scad, **defines)
        assert not r.ok, f"{scad} {defines} rendered, but an assert should have stopped it"
        assert match in r.log, f"expected {match!r} in the render log:\n{r.log[-800:]}"
        return r


@pytest.fixture
def openscad(tmp_path) -> OpenSCAD:
    if not osc.available():
        pytest.skip(f"OpenSCAD not found; set {osc.ENV}")
    return OpenSCAD(tmp_path)
