# Project Plan

## Mission
Build an independent, provider-neutral, local-first Private AI platform whose corpus, task state, knowledge and memory remain usable when any optional model host, cloud provider, GPU, network, browser or MCP server is unavailable. Preserve `/mnt/private-ai-data/privateai/repo/` as immutable raw evidence.

## Ordered phases and status (2026-10-04)

| Phase | Deliverable | Status | Verification required |
|---:|---|---|---|
| 0 | Historical and machine audit | COMPLETED (bounded) | Evidence report created; unknowns and non-exhaustive areas stated. |
| 1 | Project layout, architecture and live recovery/control plane | VERIFIED | Required progress files/docs exist; current task and exact recovery command are persisted. |
| 2–3 | Deterministic raw-corpus inventory and stable repository IDs | VERIFIED | 351/351 top-level entries; 434/434 file hashes; repeat IDs stable; all 352 SQLite DBs healthy. |
| 4 | Safe bounded extraction framework | PENDING | Signature detection, path/symlink/resource limits, recursive queue and failure recording. |
| 5–7 | Recursive extraction, content parsing and per-file Markdown records | PENDING | Fixture-based coverage by format; no silent skips or source modification. |
| 8–10 | Per-item SQLite, global SQLite, deduplication and completeness audit | PENDING | Foreign keys, indexes/FTS, reconciliation counts, hash stability and recovery. |
| 11 | Legacy knowledge import | PENDING | Provenance, duplicate/conflict handling and secret screening. |
| 12–13 | Offline-capable research queue and durable memory | PENDING | Cached research, durable queue, restart recovery, explicit source confidence. |
| 14–16 | Provider/model registry, tools/skills/MCP, orchestrator and agent runtime | PENDING | Provider-neutral contracts, local fallback and failure tests; Ollama optional only. |
| 17–20 | CLI, API, web UI and VS Code extension | PENDING | Shared backend contracts and integration tests. |
| 21–24 | Browser/computer/voice, workers, diagnostics, deployment | PENDING | Permission controls, service recovery and health checks. |
| 25 | Full security, completeness and production audit | PENDING | No unsupported completion claims; all unresolved limitations enumerated. |

## Immediate dependency chain

1. Complete historical findings and document machine/runtime inventory.
2. Finish safe inventory runner and persist counts/IDs/manifests/databases.
3. Verify raw source hashes and stable IDs on a second pass.
4. Build bounded recursive extraction with per-member journaling and refusal records.
5. Add extraction fixtures and real-corpus pilot; only then scale workers.
6. Parse and emit knowledge records with exact provenance.
7. Reconcile all inventory, extraction, database and Markdown totals.

## Operating constraints

- Do not execute corpus binaries, package scripts, install scripts, or repository code during extraction.
- Do not modify raw corpus items. Generated outputs belong outside `repo/`.
- No credentials in code, docs, logs, databases, prompts or corpus-derived outputs. Never use credentials found in prompts/history.
- Avoid dependency installation until the selected pipeline has been measured against installed tools and representative fixtures.
- Keep SQLite as the durable base; vector/search accelerators are optional and rebuildable.
- An item status can be COMPLETED only after output and database consistency checks; VERIFIED requires independent verification.
