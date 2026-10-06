# Effort Estimate (rough, assumptions-based)

**Created:** 2026-10-06
**Updated:** 2026-10-06 — row 1 (text-parser backlog) replaced with **measured** throughput.
**Status:** ESTIMATE ONLY — not verified project data. Rows 2–12 remain estimates.

> **Important:** No effort figure in hours is recorded anywhere in this repository's control
> plane; the project's stated convention is measured evidence ("counted, not estimated").
> Rows 2–12 below are estimates produced by an assistant from the phase descriptions in
> `docs/PROJECT_PLAN.md`, `.progress/TASK_QUEUE.md`, and
> `old-dev/private-ai/plan/PRIVATE_AI_BUILD_ROADMAP.md`. They are **not** project-recorded data.
> Row 1 is now backed by a direct measurement (see below). Accuracy on the unmeasured rows is
> roughly **±50 %**; treat ranges, not point values.

## Measured data (2026-10-06)

Direct measurement of one bounded parser tranche, using the documented next-action command:

```bash
python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120
```

| Metric | Measured value |
|---|---|
| Batch wall time | **60.438 s** for 1,000 outputs (≈ **16.5 rows/s**, ≈ **993 rows/min**) |
| Result mix | 850 PARSED, 98 SENSITIVE, 42 BINARY, 9 UNSUPPORTED_TYPE, 1 TOO_LARGE, **0 errors** |
| Parser rows | 84,968 → **85,968** (+1,000) |
| Pending (provenance-aware) | 145,817 → **144,817** (−1,000) |
| Markdown files | 69,061 → **69,911** (+850, equals new PARSED) |
| Global DB size | +663,552 bytes (**≈ 648 KB per 1,000 rows**) |
| Reconciliation pass (`--verify --offset 0 --limit 1000`) | **1.800 s** for 1,000 rows, **0 issues** (≈ 1.8 ms/row) |
| SSD scratch | device 2050 vs project device 2081; 936,331,341 bytes used (<20 GiB); probe verified |

**Extrapolation from measured data:**

- Remaining backlog 144,817 outputs ÷ 993 rows/min ≈ **146 min ≈ 2.4 h** of pure machine time
  (~146 back-to-back 1,000-row batches).
- A full 1,000-row reconciliation pass is ~1.8 s; a full-queue audit over 230,785 rows ≈ **7 min**
  of machine time.
- Backlog adds ≈ 94 MB to the 458 MB DB (negligible against the 20 GiB scratch cap).

**Measurement caveats:** one tranche at a representative content mix; throughput may shift with
file-type composition (capped at 2 MB/member). This covers the UTF-8 text parser only — it does
**not** cover the 37 BLOCKED / 63 FAILED extraction jobs, the four sidecar discrepancies, or
specialized formats (rows 2–3), which remain the real uncertainty. Human cost is now the
checkpoint-and-verify loop, not raw runtime.

## Assumptions (all of them)

- One experienced senior engineer, working with AI coding assistance, on the critical path
  (no other developers, no handoffs).
- "1 day" = 6–8 productive hours; hours below use 8 h/day.
- Sequential / critical-path execution; limited parallelism.
- Excludes time blocked on external decisions (skill-format gate `O-002`; `TRIGGER-0001`'s need
  for a persistent terminal session).
- Core scope = the live control-plane tasks plus the final audit. Optional scope = build-roadmap
  phases beyond the live plan.

## Remaining work — core scope

| # | Workstream | Low (days) | High (days) |
|---|---|---:|---:|
| 1 | Finish text-parser backlog — `CORPUS-0006` (144,817 remaining; **measured ~2.4 h machine time**, so cost is supervision/checkpointing) | 0.5 | 1 |
| 2 | Specialized parsers: PDF/Office/OCR, code AST/symbols, media metadata | 8 | 15 |
| 3 | Close extraction gaps — 37 BLOCKED + 63 FAILED jobs, 4 sidecar discrepancies in REPO-0154/0329, full original-candidate re-audit | 3 | 6 |
| 4 | `CORPUS-0007` — reconcile DBs, duplicates, totals, FTS | 3 | 6 |
| 5 | `CORPUS-0008` — legacy knowledge import + secret screening | 5 | 10 |
| 6 | `RESEARCH-0001` — offline-resilient research queue/worker | 5 | 10 |
| 7 | `MEMORY-0001` — durable portable memory + retrieval | 8 | 15 |
| 8 | `DEV-0002` — provider registry/health/routing/fallback | 6 | 12 |
| 9 | `DEV-0003` — tool/skill registry, permissions, approvals, agents | 10 | 20 |
| 10 | `DEV-0004` — CLI/API/web/VS Code + deployment | 15 | 30 |
| 11 | `TRIGGER-0001` — background worker runtime verification | 1 | 3 |
| 12 | Final security / completeness / production audit (phase 25) | 5 | 10 |
| | **Core subtotal** | **69.5** | **138** |

**Core total: ~70–138 engineer-days ≈ 560–1,100 hours.**

## Optional / later scope (build roadmap beyond the live plan)

Browser automation, computer use, voice/video, connector ecosystem, background daemon, Obsidian
integration, autonomous operation (build-roadmap phases 20–27 plus cross-cutting additions):
**+25–60 days ≈ 200–480 hours.**

**All-in total: ~95–198 engineer-days ≈ 760–1,590 hours** (roughly 4–9 months solo).

## Notes on the shape of the work

- **Critical path:** corpus parsing → `CORPUS-0007`/`0008` → memory/retrieval → provider layer
  → tools/agents → user surfaces. The product runtime cannot meaningfully start until the corpus
  foundation clears.
- **Largest remaining unknown (revised):** specialized parsers (row 2) — now the widest band.
  No OCR/PDF/Office/Tika/Java tooling is installed yet, and fixtures plus tests must be built per
  format. The text-parser backlog (row 1) is **no longer** a significant uncertainty.
- **Smallest, cheapest win:** `TRIGGER-0001` (1–3 days) once a persistent terminal is available.

## Revision log

- 2026-10-06 — initial estimate created.
- 2026-10-06 — measured one parser tranche end-to-end; replaced the row-1 estimate (was 3–5 days)
  with measured throughput and reconciliation timing. Core subtotal moved 72–142 → 69.5–138 days.
  Note: running the measurement advanced the corpus by one tranche (parser rows 84,968 → 85,968),
  control-plane docs were reconciled to the measured state in the same session (85,968 rows / 144,817 pending).

## Caveat

This file exists only as a planning aid alongside the control-plane documents. It does not
change any task status, does not imply completion of any phase, and should be superseded by
broader measured throughput data as more tranches are captured.
