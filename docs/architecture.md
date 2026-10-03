# Architecture

printgate judges a print before it happens: a model before it is sliced, G-code before it is
sent. Every judgement is a `Finding` with a stable check id and a severity; everything learned
about one subject is a `Report`.

## What belongs here

Deterministic checks. The admission test: could the rule be written down precisely enough that
two independent implementers, given the same file and profile, reach the same verdict? A rule
that needs the words "use judgment" stays out, or becomes a threshold in the profile.

Tools that already do a job well are adapters, not reimplementations.

## Code map

`src/printgate/__init__.py` is the public surface. Anything it does not export is internal.

- `contract.py` holds the findings and reports every part speaks, and the ports adapters
  implement: `MeshAnalyzer`, `Slicer`, `Differ`, `Reporter`. It imports nothing else here.
- `profile.py` holds the printer limits and thresholds, and the firmware dialects.
- `config.py` finds the project configuration: the printers, each a profile plus how to slice
  for it.
- `gcode/` reads G-code. `parse.py` turns a file into a toolpath in one pass; `checks.py` is one
  pure function per failure mode over that toolpath.
- `mesh.py` holds the checks on mesh metrics, whichever analyzer measured them.
- `scad/` runs OpenSCAD (`openscad.py`) and provides the pytest plugin (`pytest_plugin.py`).
- `adapters/` wraps external tools behind the ports. Each imports its tool lazily, so a missing
  optional dependency only fails the command that needs it.
- `reporters/` formats reports. They read the contract and nothing else.
- `review.py` drives a model through render, measure, picture and slice.
- `plugins.py` finds adapters and reporters by name; `cli.py` is the command line.

## Invariants

- Imports point one way: `cli` → `review` → `gcode`, `mesh`, `scad`, `adapters` → `config` →
  `profile` → `contract`. Reporters depend on `contract` only. Nothing in the core imports an adapter; `review` resolves them by name through `plugins`.
- A check is a pure function of its input and the profile. The same file and profile always
  yield the same findings, in the same order.
- Check ids are part of the interface: reporters and CI scripts key on them. Renaming one is
  a breaking change. A finding from slicing for one printer keeps its id and names the printer
  in its data.
- Thresholds live in `Profile`, never inline in a check.
