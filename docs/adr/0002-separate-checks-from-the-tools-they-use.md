# 0002. Separate checks from the tools they use

Status: Accepted
Date: 2026-10-03

## Context

The code began as scripts in one person's print workflow. They hard-coded one printer's limits,
one slicer, one mesh library and one output format into the same functions as the rules
themselves. Mature tools already exist for most of the surrounding work: trimesh for meshes,
PrusaSlicer for slicing, argus-diff for geometric diffs. The rules (when does a first layer
detach, when have parts fused) exist nowhere else.

## Options

- **One module per command.** Simple, but each command re-implements reading and reporting, and
  the printer's limits stay inline.
- **By kind** (`utils/`, `models/`, `services/`). Familiar, but `utils/` collects everything and
  nothing stops it importing a feature.
- **By role, with ports and adapters.** The contract and profile at the bottom, pure checks above
  them, external tools behind small protocols at the edge, reporters reading only the contract.
  Each folder hides one decision likely to change: a threshold, an input format, a tool, an
  output.

## Decision

Lay the package out by role, as `docs/architecture.md` describes. External tools enter only as
adapters implementing a port in `contract.py`, found by entry point. Thresholds move into
`Profile`.

## Consequences

A new slicer, mesh library or output format is a new adapter or reporter, possibly in another
package, with no change to the checks. A misplaced module shows up as an import pointing the
wrong way. Nothing enforces the import rule yet; an import-linter contract would.
