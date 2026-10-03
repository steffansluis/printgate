from printgate import mesh
from printgate.profile import Profile

OK = {"Width X (mm)": 50.0, "Depth Y (mm)": 50.0, "Height Z (mm)": 5.0,
      "Thinnest wall (mm)": 1.6, "Bodies": 1, "Watertight": "yes"}


def ids(metrics, profile=Profile()):
    return {f.check for f in mesh.checks(metrics, profile)}


def test_a_sound_part_has_no_findings():
    assert ids(OK) == set() and mesh.fits(OK, Profile()) is None


def test_thin_walls_and_stray_bodies_warn():
    assert ids(OK | {"Thinnest wall (mm)": 0.5, "Bodies": 2}) == {"thin-wall", "bodies"}


def test_bed_fit_follows_the_profile():
    tall = OK | {"Height Z (mm)": 260.0}
    assert mesh.fits(tall, Profile(bed_max=(220, 220, 250))).check == "bed-fit"
    assert mesh.fits(tall, Profile(bed_max=(220, 220, 280))) is None
