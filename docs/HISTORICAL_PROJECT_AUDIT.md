# Historical Project Audit

**Audit scope:** `/mnt/private-ai-data/privateai/old-dev/` (read-only review); audited 2026-10-04. The authoritative source trees were preserved.

## Scope and measured structure

| Tree | Observed files | Disk use | Findings |
|---|---:|---:|---|
| `private-ai/` | 6,603 | 211 MiB | Older campaign workspace with scripts, plans, skills, API references, project state, and a large evidence/knowledge tree. |
| `private-ai-backup/` | 1 archive | 6.1 GiB | A single dated backup ZIP. Not opened or restored during this audit. |
| `private-ai-ds/` | 1,867 | 24 MiB | Substantial Python runtime with source, tests, migrations, docs, deployment examples, and a Git repository. |
| `private-ai-extractions/` | 1 marker file counted | 32 KiB | Empty/near-empty extraction mount layout (`audio`, `video`, `cache`, `work`, `large-files`, `archives`). |
| `knownldge/` | 6,597 | 210 MiB | Knowledge/evidence tree closely resembling `private-ai/`; includes source indexes, decisions, research, skills, architecture, and thousands of work/evidence files. |

The `private-ai-ds` Git tree is **not clean**: 13 tracked modifications and 2 untracked paths were observed. Its HEAD was `80de8aa`; the current worktree includes an uncommitted OpenAI-compatible adapter and tests. Do not treat HEAD or prior status documents as a complete snapshot, and do not overwrite these changes. The active workspace root is not itself a Git repository. The raw corpus has 351 actual top-level entries; its raw contents are evidence and must remain unchanged.

## Reusable ideas and code (inspect before adopting)

- **Agent runtime:** typed task lifecycle, durable checkpoints/recovery, idempotency, bounded execution, cancellation, planning, verification, append-only audit, and explicit permission/approval boundaries in `private-ai-ds/src/private_ai/`.
- **Persistence:** standard-library SQLite, explicit migrations, foreign-key enforcement, repository modules, backup/restore, and diagnostic checks.
- **Ingestion:** `ingestion/` includes bounded extraction, path screening, worker leases, crash recovery, provenance, indexing, watcher reconciliation, retention and refusal/error records. This is strong reference material for safe corpus ingestion; it does not yet satisfy broad package coverage in this workspace.
- **Provider boundary:** `models/base.py`, `registry.py`, `routing/`, `stub.py`, `openai.py` (the latter is currently untracked in that historical worktree), embeddings, and failover abstractions. The OpenAI-compatible adapter is a candidate, not verified committed history.
- **Interfaces and operations:** CLI/HTTP adapters, configuration validation, `doctor`, memory, skills inventory, evaluation fixtures, systemd watcher examples, and substantial tests (38 named test files were discovered).
- **Architecture and decisions:** `ARCHITECTURE.md`, `CONFIGURATION.md`, `SECURITY.md`, `PRODUCTION_READINESS.md`, the project audit, 41 ADR files, numbered SQL migrations, and failure/recovery tests.
- **Knowledge:** `knownldge/data/` and `private-ai/data/` contain source registries, duplicate analyses, recovery notes, ADR indexes, code patterns, integration catalogs, research notes, and extracted repository work. Import only with provenance, hash-based duplicate detection, and secret screening.

## Risks, failures, limitations, and unresolved questions

- The prior runtime's settings still expose `provider=stub|ollama`, default Ollama-specific configuration, and an Ollama embedding adapter. The architecture must not depend on this host path; the replacement needs independent adapters and tested offline/degraded modes.
- Prior audit reports describe a mature but incomplete runtime, not a production-ready end-user product: no shipped web UI or VS Code extension, narrow tools, and gaps in installation/service operation. Statements in inherited documents are historical claims until re-run in this workspace.
- `private-ai-ds` is dirty, so its tracked and untracked work must be reconciled before copying or building on it. Never blindly merge it.
- `private-ai/` and `knownldge/` each report roughly 6.6k files and similar sizes. They may contain overlapping content, but equivalence is **not established**. Compare manifests and hashes; preserve both sources and their separate provenance.
- The 6.1 GiB backup was not inspected. Its contents and safety status are unknown; do not unpack it over live data.
- Historical artifacts include private API/configuration material. Credential-shaped content has been observed in the historical prompt material. Do not copy these values, index them, print them, or commit them; handle only redacted findings and rotate any exposed credentials through their owner-controlled process.
- Prior progress logs cite remote Ollama instances and one-off test results. Those are not portable evidence for this Linux machine.
- Old research notes include assertions about package identity, revisions, source counts, and capability. Validate claims against actual artifact contents; filenames and archive roots are not identity proof.
- Windows-specific assumptions exist in user narratives (Windows host, LAN Ollama, workstation availability). None is an acceptable runtime dependency here.
- Dependency assumptions in `private-ai-ds/pyproject.toml` claim a zero-runtime-dependency Python 3.11+ core with optional extras. The current environment is Python 3.14.4 and has a partial parser library set; compatibility and runtime tests remain necessary.

## Structures, integrations, and files inspected

Inspected tree listings, source/test/deploy file names, and selected architecture, audit, readiness, configuration, security, provider and ingestion files. Verified named integration surfaces include SQLite, Ollama, OpenAI-compatible HTTP, embeddings, stdlib HTTP API/CLI, filesystem/shell tools, Python packaging, and example systemd watcher units. No service was installed or started. Exact runtime behavior and API coverage require tests in the active workspace.

## Audit disposition

**Reusable as design/reference:** permissioned agent loop, typed model/tool boundaries, SQLite migration discipline, crash-safe worker patterns, idempotent recovery, provenance, and extensive negative testing.

**Replace or revalidate:** Ollama-first configuration/defaults; references to external workstation IPs; stale completion/readiness claims; undifferentiated historical data imports; any executable/shell-based corpus “analysis” workflow.

**Not yet audited exhaustively:** every file's content, the backup archive internals, all source indexes and queue rows, exact overlap between the knowledge trees, all migrations/test gates, and every secret-bearing file. This report is an evidence-bounded audit, not a claim that every historical file was read.
