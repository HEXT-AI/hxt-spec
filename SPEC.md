# .hxt File Format Specification

**Version**: `0.1.0`  
**Status**: Draft  
**License**: MIT © Gemmina Intelligence LLC

## Overview

`.hxt` is a Markdown-based format for storing a tamper-evident authorship ledger at the end of a document. The body remains normal Markdown, while the ledger records metadata about save events:

- when the document was saved
- whether the save was classified as `AI` or `HUMAN`
- how large the change was
- the hash of the resulting body text

The ledger never stores the body text itself.

## Required Markers

Every `.hxt` file must place its JSON ledger between these exact markers:

```text
<!--hxt:begin-->
<!--hxt:end-->
```

These markers are mandatory and case-sensitive.

## File Structure

```text
[Markdown body]

<!--hxt:begin-->
{
  "hxt_version": "0.1.0",
  "genesis": "<ISO 8601 UTC>",
  "ledger": [<Step>, <Step>, ...],
  "final_seal": {<Seal>}
}
<!--hxt:end-->
```

Everything between `<!--hxt:begin-->` and `<!--hxt:end-->` must be valid JSON.

## Hashing Rules

The reference implementations normalize the body text in the same way before hashing:

1. Remove any existing `.hxt` block.
2. Use only the Markdown body above `<!--hxt:begin-->`.
3. Trim trailing whitespace immediately before the marker block.

Two hash forms are used:

- `Step.hash`: first 16 lowercase hexadecimal characters of the SHA-256 hash of the normalized body
- `final_seal.state_hash`: full SHA-256 hash of the normalized body, prefixed with `sha256:`

## Schema

### Root Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hxt_version` | string | Yes | Semantic version in `MAJOR.MINOR.PATCH` form |
| `genesis` | string | Yes | First save timestamp in ISO 8601 UTC form |
| `ledger` | array | Yes | Ordered array of step objects |
| `final_seal` | object | Yes | Integrity record for the current body |

### Step Object

One step is appended for each save event.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `t` | integer | Yes | Unix timestamp in whole seconds (UTC) |
| `type` | string | Yes | `AI` or `HUMAN` |
| `delta` | integer | Yes | Character count change compared to the previous body |
| `hash` | string | Yes | First 16 hex chars of the SHA-256 hash of the resulting body |

### Seal Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sealed_at` | string | Yes | Last save timestamp in ISO 8601 UTC form |
| `human_touch` | number | Yes | Weighted ratio of human edits from `0.0` to `1.0` |
| `state_hash` | string | Yes | Full SHA-256 of the normalized body, prefixed with `sha256:` |
| `step_count` | integer | Yes | Total number of steps |

## Type Classification

When the caller passes `auto`, the reference implementations classify a save as:

- `AI` when `abs(delta) > 500` and `elapsed_ms < 2000`
- `HUMAN` otherwise

When the caller passes `AI` or `HUMAN` explicitly, that value is used as-is.

## Human Touch Score

`human_touch` is calculated identically in JavaScript and Python:

```text
human_delta = sum(abs(step.delta) for HUMAN steps)
total_delta = sum(abs(step.delta) for all steps)

if total_delta == 0:
  human_touch = 0.0
else:
  human_touch = round(human_delta / total_delta, 3)
```

## Canonical Example

The following example is structurally valid and matches the bundled `examples/sample.hxt` body hash.

```markdown
# Q3 Business Review

This quarter we achieved disciplined growth while reducing support backlog and improving launch velocity.

<!--hxt:begin-->
{
  "hxt_version": "0.1.0",
  "genesis": "2026-04-01T09:00:00Z",
  "ledger": [
    {
      "t": 1743501600,
      "type": "AI",
      "delta": 210,
      "hash": "25d5d98e6df4c5b8"
    },
    {
      "t": 1743503400,
      "type": "HUMAN",
      "delta": -120,
      "hash": "8e9fdc4d3171ab27"
    },
    {
      "t": 1743507000,
      "type": "HUMAN",
      "delta": 390,
      "hash": "7b3ee374c08e6023"
    }
  ],
  "final_seal": {
    "sealed_at": "2026-04-01T10:30:00Z",
    "human_touch": 0.708,
    "state_hash": "sha256:7b3ee374c08e6023e78fdaa35719a8abda60743e8a45a65ecf7abda55c0461c3",
    "step_count": 3
  }
}
<!--hxt:end-->
```

## Verification Rules

A `.hxt` file is considered **valid** when all of the following are true:

1. Both required markers are present in the correct order.
2. The ledger JSON parses successfully.
3. `hxt_version` matches semantic version format.
4. `genesis` and `final_seal.sealed_at` are valid ISO 8601 UTC timestamps.
5. `ledger` is a non-empty array of valid step objects.
6. `final_seal.step_count` equals the number of steps.
7. `final_seal.human_touch` equals the score recalculated from the ledger.
8. The last step hash equals the first 16 hex chars of the current body hash.
9. `final_seal.state_hash` equals the full current body hash.

Validation outcomes:

- `ok`: all checks pass
- `malformed`: schema or format rules fail
- `tampered`: the current body hash does not match the stored hash values

## Reference Files

- `hxt.js`: JavaScript reference implementation for Node.js and browsers
- `hxt.py`: Python reference implementation and CLI
- `examples/sample.hxt`: valid example file
- `examples/invalid.hxt`: intentionally tampered example file

## License

MIT © Gemmina Intelligence LLC
