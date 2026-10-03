from pathlib import Path

from printgate.contract import Finding, Image, Report, Severity
from printgate.reporters.markdown import MARKER, MarkdownReporter


def report(**kw):
    return Report("m.scad", metrics={"Volume (cm³)": 2.0, "Watertight": "yes"}, **kw)


def test_marker_leads_so_the_comment_can_be_updated_in_place():
    assert MarkdownReporter().render([]).startswith(MARKER)


def test_deltas_against_the_baseline():
    md = MarkdownReporter().render([report(baseline={"Volume (cm³)": 1.6, "Watertight": "no"})])
    assert "| Volume (cm³) | 2.0 | +0.4 (+25%) |" in md
    assert "| Watertight | yes | was no |" in md


def test_without_a_baseline_everything_is_new():
    assert "| Volume (cm³) | 2.0 | new |" in MarkdownReporter().render([report()])


def test_images_point_at_the_asset_url():
    r = report(images=[Image("iso", "isometric", Path("out/m/iso.png"))],
               findings=[Finding("first-layer", Severity.WARN, "small")])
    md = MarkdownReporter("https://example.org/a/").render([r])
    assert "![iso](https://example.org/a/m/iso.png?raw=true)" in md
    assert "⚠️ **first-layer**: small" in md


def test_info_findings_stay_out_of_the_comment():
    md = MarkdownReporter().render([report(findings=[Finding("shape", Severity.INFO, "21 layers")])])
    assert "21 layers" not in md
