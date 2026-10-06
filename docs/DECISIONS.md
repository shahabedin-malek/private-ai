# Architecture Decisions

## D-001 — Raw repository corpus is immutable
**Accepted.** Source: user requirement. All generated work goes outside `repo/`. Inventory reads via lstat/open and never renames or extracts in place.

## D-002 — Stable IDs are manifest identities, not filenames
**Accepted.** Assign by deterministic sorted path on initial discovery. Persist path/device/inode associations and never recycle an allocated ID.

## D-003 — Ollama is optional, never a dependency
**Accepted.** Source: user requirement and historical LAN-host failure. Core provider protocol must not assume Ollama or any other single vendor/host. An offline/no-model mode remains useful.

## D-004 — SQLite plus portable files is the durable foundation
**Accepted.** Keep structured records in SQLite, canonical large content on disk with hashes, and human-readable Markdown for inspection. Specialized indexes remain optional/rebuildable.

## D-005 — Historical code is evidence, not an automatic merge source
**Accepted.** `old-dev/private-ai-ds` contains valuable runtime code but its Git tree is dirty and has provider-specific assumptions; audit first, selectively reimplement/adapt with tests.

## D-006 — Secrets are never materialized into new artifacts
**Accepted.** Historical inputs contain credential-shaped material. Do not copy, expose, log, index or commit secret values. Only record redacted findings and use secret references.

## D-007 — No automatic dependency installation or payload execution
**Accepted.** Inspect installed tools and select from evidence. Parse/inspect untrusted source statically; never run arbitrary corpus code to understand it.
