# Model Architecture

## Non-negotiable boundary

The core imports a provider protocol, not Ollama/OpenAI/Anthropic/Gemini SDKs. Ollama may be added only as an optional adapter. It is never the sole provider or a required service. A lost provider, API key, network, GPU or model must not prevent the CLI, corpus databases, lexical retrieval, memory storage or cached/offline work from operating.

## Registry record

A model registration describes provider/model/endpoint reference, local/remote/data policy, supported capabilities, context/output limits, tool/vision/structured-output features, price estimate, latency estimate, priority, health, fallback order, last success, failure count, version, quantization and hardware requirements. Unknown capabilities are false/unknown, never inferred from model name.

## Routing

1. Filter by requested capability and data policy.
2. Check health and hardware/resource budget.
3. Order eligible candidates by configured priority and measured reliability.
4. Apply timeouts, bounded retries, circuit breaking and deterministic fallback.
5. Record token/latency/cost/tool/error usage without secret values.
6. Report degraded/unavailable state truthfully; do not claim an LLM answer when a stub or cache was used.

## Adapter roadmap

Potential adapters after protocol/tests: llama.cpp/llama-server, vLLM, Hugging Face Transformers, OpenAI-compatible endpoints and optional hosted provider adapters. Embedding, reranker, speech, vision and image/video-generation contracts are separate capabilities. Support only after each adapter has offline/health/failure tests and explicit egress policy.

## Hardware policy

Detect available RAM, CPU extensions, GPU/runtime and disk at startup; select a compatible small local model or CPU mode where configured. Never imply unlimited compute. Current host: x86_64 Ubuntu, 6 CPU cores, about 17 GiB RAM, ~768 GiB free on the data mount, AMD Radeon HD 7750/8740 / R7 250E detected by PCI; CUDA/NVIDIA runtime absent. No local model runtime or model files were detected. Consequently no semantic local inference is available yet; provide useful corpus/CLI functions without a model.
