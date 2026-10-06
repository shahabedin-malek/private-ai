# Research Architecture

Research is a later phase, separate from interactive chat. Store configurable search terms and queued queries in SQLite; record URL/source, retrieval timestamp/hash/status/parser, claims/entities/relationships, confidence, provider/model/token usage and duration. Prefer official repositories/docs and primary papers; rank source quality and retain citations.

Cache unchanged content by content hash/validators. If offline, continue local extraction and leave web jobs queued with bounded backoff. One unavailable source/provider cannot stop other work. Workers use durable leases, heartbeats, retries, checkpoints and health status. Do not deploy a 24/7 service until its data model, safety controls and restart tests exist.

Status: architecture only; no research worker or scheduler is implemented in the active workspace.
