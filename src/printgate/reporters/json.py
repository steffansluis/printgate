from __future__ import annotations

import json
from dataclasses import asdict

from ..contract import Report


class JsonReporter:
    def render(self, reports: list[Report]) -> str:
        return json.dumps([asdict(r) | {"blocked": r.blocked} for r in reports],
                          indent=1, default=str) + "\n"
