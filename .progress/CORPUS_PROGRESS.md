# Corpus Progress

**Live status (2026-10-06)** — supersedes the early snapshot below where they conflict:

- Extraction: global DB 365 jobs — 265 VERIFIED, 37 BLOCKED, 63 FAILED — with 230,785 EXTRACTED outputs; additive `repo/new/` subset 58 VERIFIED / 10 fail-closed FAILED.
- Text parsing: `stdlib-text-v3` **85,968** rows (69,911 PARSED, 10,040 SENSITIVE, 3,596 UNSUPPORTED_TYPE, 2,220 BINARY, 179 TOO_LARGE, 22 UNSUPPORTED_ENCODING); **144,817** provenance-aware pending; **69,911** Markdown files; outbox 0; global integrity `ok`, FK 0.
- Per-file Markdown is **no longer zero** — 69,911 files exist. Full parser audit remains due; specialized formats/OCR/AST remain pending.
- No archive payload code was run and raw corpus was not intentionally modified.

**The bullets below are an early snapshot retained only as provenance; they contain stale counts.**

- Raw path: `/mnt/private-ai-data/privateai/repo/` (preserve unchanged).
- Current source root: **350** top-level entries (349 regular files + one directory). That directory contains 5 subdirectories and nested files. Current recursive regular-file count is **433**.
- Stable IDs remain **351** (`REPO-0001`…`REPO-0351`); do not renumber. The manifest still includes active REPO-0159 `entire_linux_arm64.tar.gz`, absent from current source. Reconcile as MISSING; do not recreate bytes.
- Baseline manifest has 434 file rows and 297 archive candidates; current extraction queue: 115 VERIFIED, 26 BLOCKED, 53 FAILED, 1 resumable IN_PROGRESS (REPO-0239), 102 unclaimed.
- Per-item SQLite DBs: 352 files found (351 workspaces + one empty extra legacy REPO-0084 DB); global DB: 1. All 353 SQLite files pass integrity/FK checks.
- Extraction fixture suite 26/26 and inventory fixtures 7/7 pass; compile checks pass. Extraction/scraping/Markdown are no longer zero: 115 archive sources VERIFIED; recursive scraping and per-file Markdown remain **0**.
- No archive payload code was run and raw corpus was not intentionally modified.
- Next: resume REPO-0239 bounded stage, continue extraction, reconcile missing REPO-0159 without ID drift.
