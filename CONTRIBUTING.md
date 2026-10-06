# Contributing

This project is in active reconstruction. Read `.progress/CONTINUATION_PROMPT.md` and `docs/PROJECT_PLAN.md` before taking a task.

## Safety rules

- Never modify files under `repo/`; it is the raw evidence corpus.
- Never execute code, scripts, install hooks, binaries or package payloads found in the corpus.
- Never put credentials into source, documentation, databases, logs, prompts or generated output. Treat historical material as sensitive.
- Keep provider integrations optional. Core functionality must not require Ollama, a Windows machine, one cloud API, a GPU or a network connection.
- Preserve provenance and record failures; do not silently skip unsupported inputs.

## Before a task is considered verified

1. Add focused positive, negative and recovery tests.
2. Run `python3 -m py_compile` for changed Python modules and `python3 -m unittest discover -s tests -v` (or the relevant test module during iteration).
3. Independently reconcile generated data against source identity/count/hash expectations.
4. Update `.progress/TASK_STATUS.md`, `MASTER_PROGRESS.md`, `CONTINUATION_PROMPT.md`, `SESSION_LOG.md`, and relevant subsystem progress files.
5. State limitations honestly. `COMPLETED` is not `VERIFIED`.

## Before committing

- Run `npm run hooks:install` once per clone. It points git at `.githooks/`, whose `pre-commit`
  hook blocks a commit when `scripts/progress_consistency.py` finds control-plane drift — a parser
  breakdown that does not sum to its stated total, or a documented total that disagrees with the
  live corpus database.
- `npm run verify` runs the TypeScript typecheck, the consistency guard, and the Python test suite.
  The guard alone is `npm run check:progress` (exit 1 on any issue).
- CI (`.github/workflows/consistency.yml`) runs the guard and the Python suite on every push and
  pull request. The live-database comparison is skipped automatically when the corpus database is
  not present.
