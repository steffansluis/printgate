# 0001. Fit to measured parts

Status: Draft
Author:
Date: 2026-10-03

## Problem

Most useful prints mate with something that already exists: a lamp holder, an extrusion, a
bracket. The model encodes that thing's dimensions as plain numbers, and nothing records where a
number came from or how far it can be trusted. A model then passes every check at the nominal
values and fails on the bench.

A typical case: a part that sits on a bought component is designed against a datasheet giving
one dimension. The rest is assumed. A feature the datasheet never mentions (a nut, a boss, a
clip) then collides with the design, and it surfaces only on the bench or when someone thinks
to scale a product photo against the one known dimension.

## Admission

Yes. Rendering a model at the ends of each measured tolerance and checking that its asserts
still hold is deterministic, given the model, the record and the tool versions.

## Proposal

1. **A measurement record** beside the model, `<model>.fit.toml`. One table per dimension, named
   after the model parameter it sets:

   ```toml
   [nut_d]
   value = 14.5
   tol = 0.7
   source = "photo"     # spec | caliper | photo | assumed
   note = "scaled from the product photo against the 37 mm body on the datasheet"
   ```

2. **A tolerance sweep.** `printgate fit MODEL` and the pytest helper
   `openscad.fits(MODEL)` render the model with each dimension at `value - tol` and
   `value + tol`, one at a time with the others at nominal. Every render must pass. A failure
   names the dimension, the end of the band and the assert that fired. That is the design rule
   the measurement is too uncertain to support.
3. **A review section** listing the record. `assumed` and `photo` entries are flagged as
   "measure before printing", and any dimension the sweep failed on is flagged as blocking.
4. **Gauges.** A model that defines `mode="gauge"` gets that render in the review, labelled as
   the print to make before the part.

## Alternatives

- **Tolerances in code comments**, the status quo. Unchecked, and they drift from the numbers.
- **CAD assembly constraints** (CadQuery or build123d assemblies). These are richer, but tied
  to one kernel, and they say nothing about how certain a dimension is.
- **Intent contracts** as partspec (github.com/heibench/partspec) has them. They are close in
  spirit. A partspec adapter could run the same records once that project stabilises.

## Trade-offs and risks

- One render per dimension end: twenty measured dimensions mean forty renders. Corners
  (every combination) grow as 2ⁿ and are deliberately left out. Two dimensions that only fail
  together are missed.
- The sweep only exercises rules the model writes as asserts. A model without asserts passes
  every sweep, so the review should say so rather than show a green tick.

## Out of scope

- Recording how a printed part actually fitted, and feeding that back into the record.
- Measuring from photos automatically.

## Open questions

- TOML beside the model, or the same data in OpenSCAD comments the tool parses?
- Should `tol` allow asymmetric bands (`tol = [-0.2, 0.7]`)?
- Does a failing sweep block a review by default, or only with `--fail-on-block`?
