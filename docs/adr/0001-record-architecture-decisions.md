# 0001. Record architecture decisions

Status: Accepted
Date: 2026-10-03

## Context

Decisions about structure outlive the conversations that made them, and a contributor arriving
later sees only the code.

## Options

- **Commit messages only.** Free, but a decision spread over several commits has no single home.
- **ADRs in `docs/adr/`**, in the short Nygard form with an explicit options section.

## Decision

Record decisions that later changes must keep to as ADRs, using `template.md`.

## Consequences

A reviewer can ask "which ADR does this change?" of any structural change.
