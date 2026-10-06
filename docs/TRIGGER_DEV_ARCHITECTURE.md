# Trigger.dev Background Execution Architecture

**Status:** Optional integration scaffold; local development task execution is not yet verified.

## Purpose and ownership

Trigger.dev adds durable background execution to Private AI; it does not replace the Python/SQLite corpus core, normal application runtime, or Freebuff/OpenCode. Freebuff/OpenCode remains responsible for coding, review, and deciding what work is safe. Existing SQLite/progress files remain authoritative; Trigger.dev runs are an execution and observability layer, not the project's sole queue or source of truth.

```text
Freebuff/OpenCode -> Private AI core and durable SQLite/progress state
                              |                     |
                              v                     v
                     Trigger.dev tasks       local CLI/workers
                     durable/optional        independent fallback
```

If Trigger.dev is unavailable, existing local CLI and worker workflows continue and persisted work can resume later. No frontend, web framework, backend API, auth integration, transcript persistence, or Realtime UI is currently implemented in this project root.

## Project and toolchain

- Trigger.dev project ref: `proj_ldxacbqsdsakdqozeqdi`.
- Config: `trigger.config.ts`; task directory: `src/trigger`; Node runtime: `node-24`; global task duration ceiling: 900 seconds.
- Installed versions: `@trigger.dev/sdk`, `@trigger.dev/build`, and `trigger.dev` CLI 4.7.2; package manager is npm with `package-lock.json`; Node 24 is required by the configured runtime and is installed in the current environment.
- `.trigger`, `node_modules`, `.env`, and `.env.*` are ignored (with `.env.example` explicitly allowed). `tsconfig.json` includes `trigger.config.ts` and `src/trigger/**/*.ts`.

## Tasks

| Task ID | Purpose | Boundaries |
|---|---|---|
| `private-ai-health` | Read-only project, SQLite, progress, scratch capacity, Node, Git, and Trigger environment diagnostic | Reports booleans/counts/space, not secrets, local absolute paths, or Git filenames; does not alter corpus |
| `private-ai-scheduled-health` | Same check on a six-hour cron schedule | Schedule takes effect only in a running/deployed Trigger worker environment; not currently registered/observed |
| `private-ai-continue` | Inspect durable progress files or optionally process one bounded parser batch | `inspect` is default; `parse-batch` requires Trigger development, parser, local writable SSD scratch, at most 100 inputs/2 MB each/60 seconds; never suitable for cloud |
| `private-ai-chat` | Optional managed Trigger `chat.agent` using Anthropic | Requires `ANTHROPIC_API_KEY` at run time; abort signal forwarded; public stream errors are sanitized; no app-side auth/transport/UI integration |
| `private-ai-retry-probe` | Explicitly failure-injecting retry demonstration | Do not trigger casually; 3 attempts, fails according to its bounded test payload |
| `hello-world` | Initializer sample | Demo only; may be removed after worker registration is verified |

All tasks are exported. Generic retries are configured for raw tasks, not the managed `chat.agent`; its retry behavior follows the SDK's chat semantics. Never wrap Trigger wait/trigger-and-wait operations in `Promise.all`.

## Local development

From the project root, run `npx trigger.dev@latest dev` (or `npm run trigger:dev`) and keep the local process active. The CLI should connect the local worker to the project's **development** environment and show discovered task IDs. Trigger.dev local tasks execute on the machine running this CLI; local files are available only in that local execution context. Stop the worker with Ctrl-C when finished.

Then trigger only the read-only `private-ai-health` task and inspect its result in the CLI/dashboard. Verify worker ready, project ref, task registration, successful run, failure visibility/retry with the explicit retry probe, and task rediscovery after restart. None of those runtime checks should be claimed until observed. Do not run `private-ai-continue` with `parse-batch` until scratch mount, quota, parser arguments, and local project root are checked for that environment.

TypeScript verification: `npm run typecheck` (`tsc --noEmit`). Focused safety tests run with `npm run test:trigger` and use Node's built-in test runner; they exercise pure health assessment and continuation guards, not Trigger runtime execution.

## Local versus cloud data boundary

The raw corpus is `/mnt/private-ai-data/privateai/repo/`; the scratch SSD is `/home/chris/data-processing/`, with a 20 GiB workspace cap. Raw corpus inputs remain immutable. Trigger.dev cloud workers cannot see either local path. `private-ai-continue` explicitly rejects `parse-batch` unless `ctx.environment.type === "DEVELOPMENT"`; the local dev worker must still be running on the actual host with the configured root and scratch mounts. Never deploy local-filesystem tasks as though cloud workers have these mounts. A future remote worker/local agent bridge requires a separately designed authenticated protocol, not an assumed shared filesystem.

The continuation task reads `.progress/MASTER_PROGRESS.md`, `.progress/CONTINUATION_PROMPT.md`, `.progress/TASK_QUEUE.md`, `.progress/TASK_STATUS.md`, `.progress/CURRENT_TASK.md`, `.progress/SESSION_LOG.md`, and `.progress/ERRORS.md` as durable context. It currently inspects availability and extracts no private next-action content into the task result. Its parser mode invokes one bounded parser tranche only; it does not run an infinite loop or overwrite progress documents.

## Queues, retries, and schedules

The scaffold uses Trigger.dev's default queue and retry behavior for ordinary task execution; no dedicated concurrency queue or cross-backend queue bridge is configured. SQLite/progress state and the existing local workers remain independent fallback paths. Keep task payloads small and free of secrets or raw corpus contents; prefer stable record IDs and idempotent bounded work. Respect retry semantics and cap attempts/duration. A six-hour health schedule is declared; no research/scraping schedule is configured. Future research workflows must use respectful request rates, caching, source hashes, bounded retries, and durable local state; choose schedule frequencies only after those workflows exist.

## Secrets and environment

No credential values belong in task payloads, logs, source control, or documentation. `.env` and `.env.*` are ignored. The chat task requires `ANTHROPIC_API_KEY` only when invoked. Trigger CLI auth and `TRIGGER_SECRET_KEY` must come from the Trigger.dev dashboard/official login flow; never invent or search random files for them. Do not use environment sync extensions or pull/show-values commands for this local-only setup. No secrets have been added by this change.

## MCP and coding-agent access

The official Trigger.dev MCP supports task listing, dev-run monitoring, run history/debugging, and (depending on mode) task triggering and deployment. Confirmed the documented OpenCode project target `opencode.json`, then ran `npx trigger.dev@latest install-mcp --client opencode --scope project --dev-only --project-ref proj_ldxacbqsdsakdqozeqdi`; the installer wrote the project config with `--dev-only` and the project ref. The MCP connection itself is not yet verified; restart OpenCode to load it. The direct server supports `--readonly`; adding it would hide `trigger_task`, so use that only for inspection-only sessions. Do not enable deployment access during setup. Trigger.dev agent skills are not installed in this checkpoint; the current skills command is `npx trigger.dev@latest skills` (the legacy `install-rules` alias is documented by the CLI).

Focused local unit tests are available as `npm run test:trigger`; they verify health status gates and continuation authorization/resource guards without invoking Trigger.dev or parsing corpus data. Current result: 5/5 pass. `npm run typecheck` also passes.

Persistent `trigger dev` remains unverified in this host: foreground attempts timed out without logs, the host does not implement background process mode, and a shell-detached CLI process did not persist. Thus task discovery, a successful `private-ai-health` run, failure/retry, and restart recovery have not been observed.

## Observability and recovery

Trigger.dev records run ID, task ID, environment, lifecycle status, attempts, duration, logs, and result/error in its run history. AI model/token/cost detail depends on provider instrumentation and is not promised by this scaffold. The health task returns structured diagnostics without credentials. For recovery, inspect the failed run and its attempt/error, correct the underlying issue, then replay/retrigger deliberately; do not retry unsafe corpus failures or use the retry probe on real work. Local corpus parser state and extraction queues remain in SQLite/progress and can be resumed through their existing local CLIs even if Trigger.dev is offline.

## Build extensions and deployment

No Puppeteer, Lightpanda, FFmpeg, apt packages, additional files, secret sync, or custom build extension is needed for these tasks. CI, preview branches, cloud deployment, and production keys are intentionally not configured. Do not deploy without a separate review of data locality, private filesystem assumptions, environment variables, retry/cost limits, and application versioning.

## Verification and known limitations

- Verified by inspection: npm manifest/lockfile; aligned Trigger.dev 4.7.2 SDK/build/CLI; project ref, `dirs`, Node 24 runtime, 900-second global duration; `.trigger`/env ignore rules; TypeScript inclusion; exported task definitions.
- Verified by execution: `npm run typecheck` passes after the task updates.
- Official CLI init confirmed the existing project is already initialized and authenticated. The official OpenCode MCP project config is installed development-only, but client connection is unverified. Local dev startup attempts timed out (45/90 seconds) without output; `nohup` did not persist through the command environment. Worker/task registration, health task success, failure/retry behavior, restart rediscovery, MCP connectivity, cloud deployment, and live cloud observability remain unverified.
- This is not a completed Private AI product runtime and does not migrate research, scraping, embeddings, OCR, or corpus processing wholesale to Trigger.dev.
