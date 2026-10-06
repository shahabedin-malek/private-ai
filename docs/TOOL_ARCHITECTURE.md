# Tool Architecture

A unified registry will describe name, version, description, source, install method, input/output schema, capability, permissions, health, last success/failure count and security classification/enabled state. Adapters may wrap MCP, CLI, Python, HTTP, filesystem, database, browser, GitHub and media tools.

A registry entry is not permission to use a tool. Runtime policy and per-task capability grants constrain invocation; effectful operations are approval-gated. Tools must be bounded, auditable and typed. Skill packages are reusable, versioned modules with declared tool needs, not duplicated prompt prose. Third-party tools are never installed or run automatically from corpus material.
