# Architecture

## Principles

1. **Offline-first and provider-neutral:** core services depend on contracts, not provider SDKs or endpoint defaults. Ollama is an optional adapter, never the only model route.
2. **Raw corpus is immutable:** ingestion reads `/mnt/private-ai-data/privateai/repo/`; all generated artifacts live in the active project workspace.
3. **SQLite is durable truth:** queue leases, hashes, task status, provenance, retries and errors survive process restarts. Search/vector accelerators are optional and rebuildable.
4. **No untrusted execution:** archive/package/script contents are data. Extraction and parsing do not execute payloads.
5. **Evidence before claims:** facts, parsed values and inferences are separately represented; an unprocessed/failed file stays visible in counts.
6. **Bounded and recoverable:** every worker has ceilings, leases, checkpoints and idempotent output identity.

## Initial runtime layers

```text
CLI / future API / Web / VS Code
               │
       application services
               │
 ┌─────────────┼─────────────────────┐
 task/agent    provider router       retrieval & memory
 permission    capability registry  tool/skill registry
 └─────────────┴─────────────────────┘
               │
      SQLite repositories + FTS
               │
     durable filesystem artifacts
```

## Corpus ingestion layers

```text
raw manifest -> hash/type detection -> durable queue/lease -> bounded recursive expansion
             -> parsers (text, source, docs, media, packages) -> provenance records
             -> per-repository SQLite + Markdown -> global SQLite/FTS -> reconciliation
```

The initial `scripts/corpus_inventory.py` is phase-scoped: it reads/hashes top-level items and descendants, assigns stable IDs and materializes workspace/database skeletons. It does not extract archives, parse arbitrary documents, or run content. Its generated state must be tested before it is treated as authoritative.

## Model/provider contract (target)

The runtime consumes capabilities such as `chat`, `reasoning`, `coding`, `vision`, `embeddings`, `reranking`, speech and generation. A provider supplies discovery, health, inference and typed failure behavior. The router checks required capability, locality/data policy, health, resource fit and configured priority; it retries boundedly and falls back without elevating permissions or disclosing data to a less-trusted provider. No provider result is required for local database, memory and cached retrieval operations.

## Deployment boundary

Local CLI/services and SQLite must operate independently of Vercel, Windows, LAN hosts and external APIs. Optional adapters are explicitly configured; credentials are references/environment/secret-store only. Systemd workers are a later deployment phase, not installed implicitly.

## Optional Trigger.dev worker boundary (2026-10-06)

Trigger.dev is an additive worker integration, not the Private AI product runtime or source of truth. The current tasks comprise read-only local health checks, a tightly bounded parser continuation allowed only in Trigger development with the local scratch workspace and parser available, an optional managed chat agent, and an intentional retry probe. No frontend, application server action, user auth, durable chat integration, or Trigger Realtime UI is wired here. Keep cloud deployment, CI automation, preview environments, environment synchronization, and cloud observability/reporting opt-in and out of scope until explicitly designed and authorized. Never send raw corpus paths/data to a remote task; unavailable local SSD/corpus must fail closed. Verify locally with typecheck before attempting a dev runner; do not run the failure-injection probe casually.

The chat agent uses Trigger's managed `streamText` flow and abort signal, and exposes only a generic UI-stream error message. Task execution and registration remain unverified until a local Trigger dev session completes successfully.

The corpus, SQLite database, and scratch-workspace boundary remains local-only; no deployment action is implied by these docs.
