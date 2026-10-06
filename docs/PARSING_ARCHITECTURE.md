# Corpus Parsing Architecture

## Scope and state

`scripts/corpus_parse.py` processes rows in global `extraction_outputs` with `status='EXTRACTED'`. It writes one provenance-bearing Markdown file per supported UTF-8 text member under `data/knowledge/files/<REPO-ID>/<extracted-file-id>.md`, and mirrors parse state to the global and corresponding per-item SQLite databases.

This is an initial text-only slice, not complete corpus scraping. It does not OCR images, parse PDFs/Office/media, unpack other packages, or extract AST/code symbols. Those files receive explicit outcomes for later parser development.

## Safety

- Verifies member hash/size against extraction provenance before parsing. A metadata size above the configured cap is rejected without reading the body; accepted text is strict UTF-8 only.
- Uses confined paths; rejects symlinks in input/output path components and atomically writes generated Markdown.
- Accepts an explicit text extension/name allowlist; no content is executed, interpreted, or HTML-rendered. Source text is fenced using a delimiter longer than any run in the content, and the member path is escaped in the Markdown heading.
- Secret screening fails closed for PEM private-key blocks, common API/token signatures, JWTs, credential-bearing URLs, bearer tokens, and non-placeholder assignments to secret-like keys. Only detection categories are recorded; detected values are not copied to Markdown or error logs. This scanner is deliberately conservative and incomplete. Placeholder forms such as `YOUR_API_KEY` remain publishable; sensitive matches are withheld for review rather than rewritten because redaction could produce misleading “faithful” knowledge.
- If a reparse changes an output to any non-PARSED outcome, an earlier generated Markdown file for that extracted member is removed before the new state is committed.

## Outcomes and crash-safe persistence

Possible durable statuses: `PARSED`, `SENSITIVE`, `UNSUPPORTED_TYPE`, `BINARY`, `UNSUPPORTED_ENCODING`, `TOO_LARGE`, `SOURCE_MISMATCH`, and `FAILED`. Each record includes repository/source/member IDs and paths, source archive and member SHA-256 values, Markdown path/hash when generated, character count, parser/version, timestamp, and safe error detail. Operational exceptions are appended to `processing_errors` in both DBs when available.

Migration `corpus-parse-v4` records the schema change, creates a durable `parse_sync_queue` outbox and parser-status lookup index. The global parse record and mirror intent commit together in a single transaction for a bounded group (128 records or 15 seconds). Per-item mirrors are upserted and read back per repository, and only then are their outbox entries acknowledged. If a process exits between either database write, the next invocation drains the outbox before selecting new work. A filesystem lock serializes parser workers so concurrent invocations cannot claim and report the same pending records. Grouped commits reduce SQLite open/commit overhead while keeping the crash-recovery boundary bounded. Migration failures are durably noted. Reprocessing is idempotent; selection retries a prior row when source/member identity or hashes differ, and verifies existing Markdown and its per-item mirror before reuse. A parser-version bump intentionally revisits prior rows.

The earlier mismatch between a batch's reported work and the immediate DB delta was not conclusively reproduced as one specific failure mechanism; concurrent duplicate selection is now prevented and cross-database crash windows are explicitly recoverable. The outbox makes mirror recovery testable, but does not make two independent SQLite databases a distributed transaction.

Every parser CLI invocation initializes and verifies `/home/chris/data-processing` through `scripts/processing_workspace.py` before working. Python `tempfile`, `TMPDIR`, `TEMP`, `TMP`, and `SQLITE_TMPDIR` are routed to its private `tmp` directory and a real fsynced/read-back/device-checked probe is performed. The default can be changed with `--scratch-root`. Canonical corpus outputs and authoritative SQLite databases remain under the project data root to retain the raw/source-of-truth layout.

## Invocation

- Single-item recovery: `python3 scripts/corpus_parse.py --project . --limit 1 --max-mb 2 --max-wall-seconds 60`
- Bounded high-throughput tranche (the CLI configures and verifies SSD scratch itself): `python3 scripts/corpus_parse.py --project . --limit 10000 --max-mb 2 --max-wall-seconds 480`
- Offline/test-only scratch on the project filesystem must be explicitly acknowledged with `--allow-same-device`; production defaults refuse the wrong filesystem.
- Continue bounded batches until completion or a durable operational error: add `--all`; never disable batch, member-size, or wall-time bounds.

Each individual member has a configurable size cap; the batch also has a wall-time budget. SQLite temporary files use `SQLITE_TMPDIR` when the runtime needs them; Markdown and authoritative DB writes remain in the project workspace. Scratch usage is measured against the 20 GiB hard cap before processing starts. The `--all` loop is foreground-only, not a supervised service.

## Checkpoint verification

Fixture tests cover exact source and Markdown hashes, provenance, global/per-item mirrors, idempotence, explicit template values, fail-closed secret matches, binary/encoding/size/type outcomes, empty text, and dynamic Markdown fences. Live checkpoint refreshed 2026-10-06 from the global SQLite database at 07:41 UTC: 198,985 EXTRACTED outputs; 67,968 rows for `stdlib-text-v3` (55,223 PARSED, 8,056 SENSITIVE, 2,964 UNSUPPORTED_TYPE, 1,543 BINARY, 161 TOO_LARGE, 21 UNSUPPORTED_ENCODING); 131,017 outputs have no current parser row; `parse_sync_queue` is empty; 55,218 per-file Markdown records are present. This direct count supersedes older figures elsewhere in historical session notes; no full current Markdown/hash/mirror audit has yet been rerun in this session. Full unittest discovery passes 54/54; compile passes. Current status supersedes any earlier figures in this document. Earlier report/DB mismatch root cause remains unproven; serialized workers and recoverable outbox mitigate concurrent selection and cross-database interruption. This remains a partial text-only rollout; remaining outputs and specialized formats are not yet processed. All extracted members still require processing and reconciliation, including database-only/unsupported outputs and error states.
