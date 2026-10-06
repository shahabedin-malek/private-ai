# Agent Architecture

The future runtime is modular, durable and permissioned. Initial components: ORCHESTRATOR (task state and delegation), PLANNER (typed plan), CODER, RESEARCHER, RETRIEVAL/MEMORY, FILE, DATABASE, TEST, SECURITY and DEPLOYMENT agents. Browser, vision and voice agents are optional extensions.

Agents request capabilities through a registry; they do not receive all tools by default. Every tool declares input/output schemas, permissions, side effects, security class, health, source/version and audit behavior. Effectful actions require policy evaluation and approval before execution. Model-produced content is untrusted input. Retrieved documents and tool outputs remain data, never instructions or permission grants.

Each task records dependencies, lifecycle state, timestamps, selected provider/model/tool versions, bounded retries, outputs, errors, verification and exact next action. Execution transitions transactionally; a task is VERIFIED only after independent checks pass. A model/provider failure yields a typed degradation or fallback, not a lost task.
