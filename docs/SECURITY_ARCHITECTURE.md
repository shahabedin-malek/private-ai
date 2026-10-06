# Security Architecture

- Treat corpus files, archives, embedded documents and model outputs as untrusted.
- Preserve raw inputs read-only; never execute discovered code, scripts, package install hooks or binaries during extraction.
- Reject traversal, unsafe links, special files, decompression bombs, resource exhaustion and archive recursion beyond configured ceilings.
- Confine writes to generated workspaces, use atomic writes and verify digests.
- Keep credentials out of source, Markdown, prompts, logs, SQLite, generated files and Git. Use secret references/environment or an OS secret store. Never echo secret values. Historical credential-shaped data is excluded from derived knowledge pending safe screening/rotation.
- Deny by default; least capability per agent/tool; separate read and side-effect permissions; approvals for destructive/external actions.
- Provider/network egress is opt-in and tied to data classification. Failures may not bypass policy by routing to a less-trusted endpoint.
- SQLite enables foreign keys and transactional state; backups and restoration are tested before deployment.
- Diagnostics report healthy/degraded/failed/unconfigured/optional distinctly and never need to disclose secrets.
