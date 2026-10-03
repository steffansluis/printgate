# printgate

@docs/architecture.md

## Writing

**Commit subject at most 50 characters, body wrapped at 72.** The body says why, not what:
the diff already says what.

**PR descriptions: 200–3200 characters, 3–33 lines.** Check with `wc -c` and `wc -l` before
posting. Over the ceiling, cut whole sections, not adjectives.

**Comments are for the non-obvious trap, at the line that traps it.** If a line is obvious,
say nothing about it.

**One home per fact.** The trap goes at the line. The decision goes in the commit body, or in
`docs/adr/` when later changes must keep to it. The argument for a change goes in `docs/rfc/`.

**No tracker IDs in source.** Describe what is wrong and why.

## Checking a change

`docs/testing.md`. A new check needs a test that trips it and a near miss that does not.
