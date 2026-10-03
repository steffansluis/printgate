"""A pull-request comment: findings, metrics with deltas, review images, parameters."""
from __future__ import annotations

from ..contract import Report, Severity

MARKER = "<!-- printgate -->"   # the comment to update in place rather than post anew
ICON = {Severity.BLOCK: "❌", Severity.WARN: "⚠️", Severity.INFO: "ℹ️"}


def _fmt(v) -> str:
    return f"{v:,.1f}" if isinstance(v, float) else str(v)


def _delta(new, old) -> str:
    if old is None:
        return "new"
    if not isinstance(new, float) or not isinstance(old, float):
        return "" if new == old else f"was {_fmt(old)}"
    d = new - old
    if abs(d) < 0.05:
        return "±0"
    return f"{d:+,.1f}" + (f" ({d / old:+.0%})" if old else "")


class MarkdownReporter:
    def __init__(self, asset_url: str | None = None, footer: str = ""):
        self.asset_url = asset_url.rstrip("/") if asset_url else None
        self.footer = footer

    def _url(self, report: Report, path) -> str:
        rel = f"{path.parent.name}/{path.name}"
        return f"{self.asset_url}/{rel}" if self.asset_url else rel

    def render(self, reports: list[Report]) -> str:
        lines = [MARKER, "## Model review", ""]
        if not reports:
            lines.append("No models changed.")
        for r in reports:
            lines += [f"### `{r.subject}`", ""]
            # Info findings repeat what the metrics table shows; a comment carries only verdicts.
            shown = [f for f in r.findings if f.severity is not Severity.INFO]
            lines += [f"- {ICON[f.severity]} **{f.label}**: {f.message}" for f in shown]
            if shown:
                lines.append("")
            if r.metrics:
                lines += ["| Metric | Value | Δ vs base |", "|---|---:|---:|"]
                base = r.baseline or {}
                lines += [f"| {k} | {_fmt(v)} | {_delta(v, base.get(k)) if r.baseline else 'new'} |"
                          for k, v in r.metrics.items()]
                lines.append("")
            if r.images:
                # ?raw=true makes github.com blob links render as images for viewers with access.
                raw = "?raw=true" if self.asset_url else ""
                lines += [" | ".join(f"**{i.caption}**" for i in r.images),
                          "|".join("---" for _ in r.images),
                          " | ".join(f"![{i.name}]({self._url(r, i.path)}{raw})" for i in r.images), ""]
            lines += [f"[{t}]({self._url(r, p)})" for t, p in r.links.items()]
            for title, text in r.attachments.items():
                lines += ["", f"<details><summary>{title}</summary>", "", "```", text, "```",
                          "", "</details>"]
            if r.parameters:
                lines += ["", "<details><summary>Parameters</summary>", "",
                          "| Name | Value | Note |", "|---|---|---|"]
                lines += [f"| `{n}` | `{v}` | {c.replace('|', '/')} |" for n, v, c in r.parameters]
                lines += ["", "</details>"]
            lines.append("")
        if self.footer:
            lines.append(f"<sub>{self.footer}</sub>")
        return "\n".join(lines) + "\n"
