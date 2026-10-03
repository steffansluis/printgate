"""Find adapters and reporters by name, including ones other packages register."""
from __future__ import annotations

from importlib import import_module
from importlib.metadata import entry_points

# The same names pyproject registers, so a source checkout works without installing.
BUILTIN = {
    "printgate.adapters": {
        "trimesh": "printgate.adapters.trimesh_mesh:TrimeshAnalyzer",
        "prusaslicer": "printgate.adapters.prusaslicer:PrusaSlicer",
        "argus": "printgate.adapters.argus:ArgusDiffer",
    },
    "printgate.reporters": {
        "markdown": "printgate.reporters.markdown:MarkdownReporter",
        "text": "printgate.reporters.text:TextReporter",
        "json": "printgate.reporters.json:JsonReporter",
    },
}


def load(group: str, name: str):
    for ep in entry_points(group=group):
        if ep.name == name:
            return ep.load()
    target = BUILTIN.get(group, {}).get(name)
    if target is None:
        found = sorted({ep.name for ep in entry_points(group=group)} | set(BUILTIN.get(group, {})))
        raise KeyError(f"no {group} named {name!r}; available: {', '.join(found)}")
    module, attr = target.split(":")
    return getattr(import_module(module), attr)
