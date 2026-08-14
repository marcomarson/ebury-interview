# <Plan Title>

> Copy this file to `ai-plans/<plan-name>.md` and fill in each section.
> If no name was provided, infer a short kebab-case name from the change.

## Metadata

| Field | Value |
|-------|-------|
| Generated Date | YYYY-MM-DD |
| AI Tool/Model | <e.g. Claude Opus 4.8> |
| Status | Draft \| Approved \| In progress \| Done |

## Summary

[Brief description of the plan.]

## Scope & Boundaries

**In Scope:**
- …

**Out of Scope:**
- …

## Implementation Details

### Steps

Ordered, concrete steps to implement the change.

1. …
2. …

### Expected Outcomes

Observable results after the change (files created, behaviour changed, data produced).

- …

### Verification Methods

How we prove it works and did not break anything.

- Automated: <test command(s), CI checks>
- Manual: <steps to confirm by hand, if any>
- Data checks: <row counts, reconciliation, sample queries, etc.>

### Unit Tests

Tests to be written. **Include edge cases explicitly.**

| Test | What it verifies | Type |
|------|------------------|------|
| … | happy path | happy path |
| … | … | edge case |
| … | invalid / malformed input | failure case |

Edge cases to cover: <nulls, empty inputs, boundary values, duplicates,
timezone/currency edge cases, precision/rounding, out-of-order events, etc.>

## Risks & Considerations

- **Risks:** …
- **Rollback plan:** …
- **Other considerations:** …

## Change Log

Any modification to this plan after it is Approved must be recorded here.

| Date | Change |
|------|--------|
| YYYY-MM-DD | Initial version |
