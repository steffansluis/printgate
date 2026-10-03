"""Review a parametric model: render it, measure it, picture it, and optionally slice it."""
from __future__ import annotations

import re
from pathlib import Path

from . import mesh, plugins
from .config import Printer
from .contract import Differ, Finding, Image, MeshAnalyzer, Report, Severity
from .gcode import preflight
from .profile import Profile
from .scad import openscad

VIEWS = [("iso", (55, 0, 25), "isometric"), ("top", (0, 0, 0), "top"),
         ("bed", (180, 0, 0), "bed side")]
SECTION = (75, 0, 15)


def parameters(scad: Path) -> list[tuple[str, str, str]]:
    """Top-level assignments that are literals or carry a comment: the model's inputs."""
    rows = []
    for line in scad.read_text().splitlines():
        m = re.match(r"^([a-z]\w*)\s*=\s*([^;]+);\s*(?://\s*(.*))?$", line)
        if m and (m[3] or re.fullmatch(r'-?[\d.]+|".*"|true|false', m[2].strip())):
            rows.append((m[1], m[2].strip(), m[3] or ""))
    return rows


def review(scad: Path, out: Path, analyzer: MeshAnalyzer, *, base: Path | None = None,
           profile: Profile | None = None, printers: tuple[Printer, ...] = (), parts: int = 1,
           differ: Differ | None = None, context: dict | None = None,
           views: dict | None = None, subject: str | None = None) -> Report:
    profile = profile or (printers[0].profile if printers else Profile())
    out.mkdir(parents=True, exist_ok=True)
    report = Report(subject=subject or str(scad), parameters=parameters(scad))
    stl = out / "part.stl"
    r = openscad.run(scad, stl)
    if not r.ok:
        report.findings.append(Finding("render", Severity.BLOCK, "render failed", {"log": r.log[-800:]}))
        report.attachments["Render log"] = r.log[-2000:]
        return report

    report.metrics = analyzer.analyze(stl)
    report.findings += mesh.checks(report.metrics, profile)
    if base is not None and base.exists():
        base_stl = out / "base.stl"
        if openscad.run(base, base_stl).ok:
            report.baseline = analyzer.analyze(base_stl)
            if differ is not None:
                report.attachments["Geometric diff"] = differ.diff(base_stl, stl)
            base_stl.unlink()

    for name, rot, caption in VIEWS:
        if openscad.image(stl, out / f"{name}.png", rot).ok:
            report.images.append(Image(name, caption, out / f"{name}.png"))
    cut = out / "section.scad"
    cut.write_text(f'intersection() {{ import("{stl.resolve()}"); '
                   'translate([-500, 0, -500]) cube(1000); }\n')
    if openscad.image(cut, out / "section.png", SECTION).ok:
        report.images.append(Image("section", "cross-section", out / "section.png"))
    # Only overrides the model declares: one setting can then serve every model in a project.
    declared = {name for name, _, _ in report.parameters}
    context = {k: v for k, v in (context or {}).items() if k in declared}
    if context and openscad.image(scad, out / "context.png", SECTION, context).ok:
        label = ", ".join(f"{k}={v}" for k, v in context.items())
        report.images.append(Image("context", f"in context ({label})", out / "context.png"))
    for name, overrides in (views or {}).items():
        if set(overrides) <= declared and openscad.image(scad, out / f"view-{name}.png",
                                                         VIEWS[0][1], overrides).ok:
            report.images.append(Image(f"view-{name}", name, out / f"view-{name}.png"))
    report.links["Open the STL"] = stl

    for printer in printers:
        if (f := mesh.fits(report.metrics, printer.profile)) is not None:
            report.findings.append(Finding(f.check, f.severity, f.message, {"printer": printer.name}))
            continue
        if printer.slicer is None:
            continue
        slicer = plugins.load("printgate.adapters", printer.slicer)(printer.slicer_config,
                                                                    printer.center)
        # Settings that travel with the model, in this slicer's own format.
        own = scad.with_suffix(f".{printer.slicer}.ini")
        overrides = (own,) if own.exists() else ()
        if overrides:
            report.attachments[f"Slicer settings from {own.name}"] = own.read_text().strip()
        gcode = slicer.slice(stl, out / f"{printer.name}.gcode", overrides)
        sliced = preflight(gcode, printer.profile, parts, printer.filament_density)
        report.metrics |= {f"{printer.name}: {k}": v for k, v in sliced.metrics.items()}
        report.findings += [Finding(f.check, f.severity, f.message, f.data | {"printer": printer.name})
                            for f in sliced.findings]
    return report
