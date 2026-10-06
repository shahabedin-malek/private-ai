# Architecture Status

**Updated:** 2026-10-06 (parser reconciled to 85,968 rows / 144,817 pending).

- Version: 0.2 corpus inventory/extraction/parser foundation; this is not the completed Private AI product.
- Source preservation: raw `repo/` is treated read-only. Original stable inventory identities exist, but the last full inventory audit is historical; REPO-0159 was recorded missing and must retain its ID.
- Stable IDs/manifests/workspaces: original and appended new repository IDs are persisted. `repo/new/` has 68 source files and 68 manifest path names; sets match exactly.
- Managed SQLite: current managed set 422 files (421 per-repository + 1 global); all passed `integrity_check` and `foreign_key_check` in the latest read-only scan.
- Extraction: bounded recursive ZIP/TAR/gzip/bzip2/xz worker supports resumable journals, safe path handling and output hashes. Global DB has 365 jobs: 265 VERIFIED, 37 BLOCKED, 63 FAILED, with 230,785 EXTRACTED output rows. This is not every corpus candidate. Additive new-source subset: 58 VERIFIED, 10 FAILED closed, 0 pending, no active lease. Ten refusals remain fail-closed; never bypass safety.
- Text parsing: `stdlib-text-v3` has **85,968 rows of 230,785 outputs**: **69,911 PARSED**, **10,040 SENSITIVE**, **3,596 UNSUPPORTED_TYPE**, **2,220 BINARY**, **179 TOO_LARGE**, **22 UNSUPPORTED_ENCODING**; provenance-aware query reports **144,817 pending**; Markdown count **69,911** and sync outbox empty. The newest 1,000 rows (offset 84,968) passed explicit Markdown hash/provenance and per-item mirror checks; full current parser audit remains due. Measured tranche: 1,000 outputs in 60.438 s (~993 rows/min). Specialized formats/OCR/AST remain pending.
- SSD scratch: `/home/chris/data-processing` is SSD `/dev/sda2` device2050 ROTA=0; project is rotational `/dev/sdc1` device2081 ROTA=1. Earlier Python defaulted to `/tmp` tmpfs. `scripts/processing_workspace.py` now routes/probes temp use and enforces 20 GiB limit for parser/new-batch CLIs. Current owned scratch staging is 936,331,341 bytes; not a system-wide configuration.
- Provider/model abstraction: documented target only; no local inference/model runtime implemented in active project. Ollama is optional, not required.
- Agent, tools/MCP/A2A, memory, research, product CLI/API/Web/VS Code, background services, voice/media and deployment remain unimplemented/unverified.
- Full test suite: 57/57 passing at previous verification checkpoint; compile passes; existing non-failing SQLite `ResourceWarning`s observed. This parser batch made no code changes. Progress/control plane has live top-level files, but older detailed historical notes may contain stale values.
- No corpus-wide or product-completion claim.
