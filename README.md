# Private AI

A private, local-first AI agent platform is the project goal. This workspace is being rebuilt incrementally from historical work and a preserved repository corpus. It does **not** yet contain a completed agent runtime, model router, API, web UI, or VS Code extension.

## Current verified milestone

- 351 actual top-level corpus items assigned stable IDs (`REPO-0001`–`REPO-0351`).
- 434 regular files have SHA-256 inventory records, independently rechecked against the read-only raw corpus.
- One per-item SQLite database and workspace for each top-level corpus entry, plus `data/database/private_ai_corpus.sqlite`.
- All 352 databases pass SQLite integrity and foreign-key checks.
- Inventory implementation and fixture suite: `scripts/corpus_inventory.py`, `tests/test_corpus_inventory.py` (7 tests).
- **No archives have been extracted and no corpus code has been executed.**

Raw corpus at `repo/` is evidence and must remain unchanged. Generated inventory is under `data/`. See `data/manifests/REPO_INVENTORY.md` and `.progress/MASTER_PROGRESS.md` for measured current state.

## Run or resume inventory

```bash
python3 -m py_compile scripts/corpus_inventory.py
python3 -m unittest tests.test_corpus_inventory -v
python3 scripts/corpus_inventory.py --root repo --output . --offset 0 --limit 40
```

Run subsequent batches with increasing offsets; completed items are checkpointed in `data/manifests/checkpoints/`. The final JSON/CSV manifests publish when all current top-level items have valid checkpoints. Output cannot be placed inside `repo/`.

## Architecture and continuation

- `docs/PROJECT_PLAN.md` — dependency-ordered phases.
- `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/EXTRACTION_ARCHITECTURE.md` — current foundation and safety boundaries.
- `docs/HISTORICAL_PROJECT_AUDIT.md` — evidence-bounded historical audit and limitations.
- `.progress/CONTINUATION_PROMPT.md` — exact next action for a fresh session.

Ollama is optional and is not installed or required. The model/provider runtime has not yet been implemented in this workspace; subsequent work must preserve useful offline, no-model operation.
