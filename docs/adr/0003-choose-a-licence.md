# 0003. Choose a licence

Status: Accepted
Date: 2026-10-03

## Context

Without a licence nobody else may use the code. The neighbouring tools it adapts or may exchange
code with are permissive: trimesh and argus-diff are MIT, PrusaSlicer is AGPL but is only run
as a separate program. Print-farm and slicer projects that might embed the checks span MIT,
GPL and AGPL.

## Options

- **MIT.** Shortest, the most common in this ecosystem, no patent clause.
- **Apache-2.0.** Permissive with an explicit patent grant and contribution terms; compatible
  with GPLv3 and AGPL projects embedding it, not with GPLv2-only ones.
- **GPL family.** Keeps derivatives open, but blocks embedding in permissive projects.

## Decision

License under Apache-2.0.

## Consequences

Contributions come under the same terms by default (section 5), so no separate contributor
agreement is needed. GPLv2-only projects cannot embed printgate; they can still run it as a
separate program, the way printgate runs PrusaSlicer.
