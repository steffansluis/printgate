from __future__ import annotations

from ..contract import Report, Severity

MARK = {Severity.BLOCK: "BLOCK", Severity.WARN: "WARN ", Severity.INFO: "info "}


class TextReporter:
    def render(self, reports: list[Report]) -> str:
        lines = []
        for r in reports:
            lines.append(r.subject)
            order = sorted(r.findings, key=lambda f: list(Severity).index(f.severity))
            lines += [f"  {MARK[f.severity]} {f.label}: {f.message}" for f in order]
            for k, v in r.metrics.items():
                lines.append(f"  {k}: {v:.1f}" if isinstance(v, float) else f"  {k}: {v}")
            lines.append(f"  {'BLOCKED' if r.blocked else 'passed'}")
        return "\n".join(lines) + "\n"
