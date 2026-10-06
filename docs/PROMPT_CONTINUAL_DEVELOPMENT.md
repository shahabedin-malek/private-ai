# Private AI — Continual Development Handoff

You are continuing the Private AI implementation from durable filesystem state. Do not rely on prior conversation or restart completed work.

## Recovery procedure

1. Read `.progress/CONTINUATION_PROMPT.md`, `MASTER_PROGRESS.md`, `CURRENT_TASK.md`, `TASK_QUEUE.md`, `TASK_STATUS.md`, `SESSION_LOG.md`, `ERRORS.md`, and `KNOWN_LIMITATIONS.md`.
2. Inspect only the next dependency's source/test files. Do not load the entire corpus into context.
3. Check actual file/database state before trusting progress prose. A task is `VERIFIED` only after independent checks.
4. Update task status, master progress, continuation prompt, session log, and relevant phase progress after each meaningful task.

## Permanent constraints

- Raw corpus: `/mnt/private-ai-data/privateai/repo/`. Do not modify it.
- No Ollama dependency. It may be one optional adapter, never a required endpoint.
- No credentials in code, Markdown, databases, logs, prompts or generated artifacts; never echo secrets found in historical files.
- Do not execute arbitrary corpus content. Extraction and analysis are data-only, confined, bounded and auditable.
- The real corpus inventory initially measured 351 top-level items. Re-check saved manifests/counts; do not assume historical estimates.
- Historical runtime `old-dev/private-ai-ds` is a useful reference but has a dirty Git worktree. Do not overwrite/copy it wholesale.

## Work sequence

Follow `docs/PROJECT_PLAN.md` and `.progress/TASK_QUEUE.md`: finish and verify inventory; implement safe resumable recursive extraction; parse supported content and produce per-file knowledge; verify per-item/global databases and FTS; then import legacy knowledge with provenance and secret screening. Only after corpus groundwork proceed through research/memory, provider abstraction, tools/agents, interfaces and deployment.

## Definition of honest progress

Record exact counts for total/discovered/extracted/partially processed/scraped/failed/blocked/pending/verified, extracted files, Markdown records, per-item DBs, global rows, duplicates, entities, and unreadable items. Report unavailability as degraded/blocked with a next action, never as completed. Do not claim installation, service operation, model support or corpus coverage without local verification.

The next executable command and current checkpoint are maintained in `.progress/CONTINUATION_PROMPT.md`.
