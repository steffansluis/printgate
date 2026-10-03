from pathlib import Path

HERE = Path(__file__).parent


def test_good_parameters_render(openscad):
    openscad.renders(HERE / "guarded.scad", width=12)


def test_assert_fires_for_bad_parameters(openscad):
    openscad.fails(HERE / "guarded.scad", "too wide for the slot", width=25)


def test_fails_rejects_a_model_that_renders(openscad):
    import pytest
    with pytest.raises(AssertionError, match="should have stopped it"):
        openscad.fails(HERE / "guarded.scad", "too wide", width=12)
