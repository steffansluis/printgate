"""printgate gcode FILE...   judge sliced G-code (exit 1 when anything blocks)
printgate review SCAD...  render, measure and picture models for a review comment
printgate comment FILE    post it to a pull request, editing the earlier one in place
"""
from __future__ import annotations

import argparse
import inspect
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from . import config as configuration
from . import plugins
from .gcode import preflight
from .profile import Profile


def _context(pairs: list[str]) -> dict:
    out = {}
    for pair in pairs:
        k, _, v = pair.partition("=")
        try:
            out[k] = float(v) if "." in v else int(v)
        except ValueError:
            out[k] = v
    return out


def main(argv=None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", type=Path, help="config file (default: PRINTGATE_CONFIG, "
                        "printgate.toml, then [tool.printgate] in pyproject.toml)")
    common.add_argument("--profile", type=Path, help="printer profile (TOML), instead of --printer")
    common.add_argument("--format", default=None, help="reporter: text, json, markdown or a plugin")
    common.add_argument("--output", type=Path, help="write the report here instead of stdout")
    ap = argparse.ArgumentParser(prog="printgate", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    try:
        ap.add_argument("--version", action="version", version=f"printgate {version('printgate')}")
    except PackageNotFoundError:
        pass
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gcode", parents=[common], help="judge sliced G-code")
    g.add_argument("files", nargs="+", type=Path)
    g.add_argument("--parts", type=int, help="separate parts the plate should hold")
    g.add_argument("--printer", help="judge against this configured printer's profile")

    r = sub.add_parser("review", parents=[common], help="review OpenSCAD models")
    r.add_argument("models", nargs="*", type=Path)
    r.add_argument("--out", type=Path, default=Path("build/printgate"))
    r.add_argument("--base-root", type=Path, help="checkout of the base revision, for deltas")
    r.add_argument("--asset-url", help="where the images will be served from")
    r.add_argument("--context", action="append", default=[], metavar="NAME=VALUE",
                   help="parameter overrides for an extra in-context view, e.g. mode=assembly")
    r.add_argument("--analyzer", default="trimesh")
    r.add_argument("--differ", help="geometric differ adapter, e.g. argus")
    r.add_argument("--fail-on-block", action="store_true")

    sub.add_parser("config", parents=[common], help="show the configuration in effect")

    c = sub.add_parser("comment", help="post a report to a pull request, editing the earlier one")
    c.add_argument("report", type=Path)
    c.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), help="owner/name")
    c.add_argument("--pr", type=int, required=True)

    a = ap.parse_args(argv)
    try:
        if a.cmd == "comment":
            from .adapters.github import upsert_comment
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            if not (token and a.repo):
                raise ValueError("needs GITHUB_TOKEN (or GH_TOKEN) and --repo or GITHUB_REPOSITORY")
            print(upsert_comment(a.repo, a.pr, a.report.read_text(), token))
            return 0
        cfg = configuration.load(a.config)
        profile = Profile.load(a.profile) if a.profile else None
        if a.cmd == "config":
            print(f"config: {cfg.source or 'none found'}")
            for p in cfg.printers:
                print(f"printer {p.name}: slicer={p.slicer} config={p.slicer_config} {p.profile}")
            return 0
        if a.cmd == "gcode":
            printer = cfg.printer(a.printer) if a.printer else None
            profile = profile or (printer.profile if printer else Profile())
            density = printer.filament_density if printer else None
            reports = [preflight(f, profile, a.parts, density) for f in a.files]
            reporter = plugins.load("printgate.reporters", a.format or "text")()
        else:
            from .review import review
            from .scad import openscad

            analyzer = plugins.load("printgate.adapters", a.analyzer)()
            differ = plugins.load("printgate.adapters", a.differ)() if a.differ else None
            reports = []
            for model in a.models:
                base = a.base_root / model if a.base_root else None
                reports.append(review(model, a.out / model.stem, analyzer, base=base,
                                      profile=profile, printers=cfg.printers, differ=differ,
                                      context=cfg.context | _context(a.context), views=cfg.views,
                                      subject=str(model)))
            cls = plugins.load("printgate.reporters", a.format or "markdown")
            offered = {"asset_url": a.asset_url, "footer": openscad.version()}
            accepted = inspect.signature(cls).parameters
            reporter = cls(**{k: v for k, v in offered.items() if k in accepted})
    except (KeyError, ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"printgate: {e}", file=sys.stderr)
        return 2

    text = reporter.render(reports)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(text)
    else:
        sys.stdout.write(text)
    blocked = any(r.blocked for r in reports)
    return 1 if blocked and (a.cmd == "gcode" or a.fail_on_block) else 0


if __name__ == "__main__":
    sys.exit(main())
