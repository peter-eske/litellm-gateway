# NVIDIA NIM API Reference (self-hosted NIM container, not API endpoint)

Source: https://docs.nvidia.com/nim/large-language-models/latest/reference/api-reference.html
Source: https://docs.nvidia.com/nim/large-language-models/latest/reference/environment-variables.html

## Inference Endpoints (vLLM-backed, OpenAI-compatible)

| Endpoint | Description |
|---|---|
| `POST /v1/chat/completions` | Multi-turn chat, supports streaming + tool calling |
| `POST /v1/completions` | Single-turn text completions |
| `POST /v1/responses` | OpenAI Responses API |
| `GET /v1/responses/{id}` | Retrieve a response |
| `POST /v1/responses/{id}/cancel` | Cancel streaming response |
| `POST /v1/messages` | Anthropic-compatible endpoint |
| `POST /v1/messages/count_tokens` | Count tokens w/o inference |
| `GET /v1/models` | List loaded models |
| `POST /tokenize` | Tokenize → IDs |
| `POST /detokenize` | IDs → text |
| `POST /v1/chat/completions/render` | Render chat template w/o inference |
| `POST /v1/completions/render` | Render prompt template w/o inference |

## Management Endpoints (NIM middleware / nginx)

| Endpoint | Description |
|---|---|
| `GET /v1/health/live` | Liveness – 200 if container running (no model needed) |
| `GET /v1/health/ready` | Readiness – 200 if model loaded |
| `GET /v1/metadata` | Active profile, model info, license |
| `GET /v1/version` | NIM release + OpenAPI version |
| `GET /v1/license` | License metadata + text |
| `GET /v1/manifest` | Model manifest with profiles |
| `GET /v1/metrics` | Prometheus metrics (latency, throughput, queue, GPU) |

## Key Environment Variables

### Model
- `NIM_MODEL_PROFILE` — Select profile; run `list-model-profiles` inside container
- `NIM_MODEL_PATH` — Model source URI (`hf://`, `ngc://`, `modelscope://`)
- `NIM_SERVED_MODEL_NAME` — Override model name in API responses
- `NIM_MAX_MODEL_LEN` — Override max context window
- `NIM_TRUST_CUSTOM_CODE` — Allow custom tokenizer/modeling code

### Server
- `NIM_SERVER_PORT` — API port (default 8000)
- `NIM_HEALTH_PORT` — Separate port for health endpoints

### Logging
- `NIM_LOG_LEVEL` — DEBUG/INFO/WARNING/ERROR/CRITICAL
- `NIM_JSONL_LOGGING` — Structured JSONL output

### CORS (nginx layer)
- `NIM_CORS_ALLOW_ORIGINS` — Default `*`
- `NIM_CORS_ALLOW_METHODS` — Default `GET, POST, PUT, DELETE, PATCH, OPTIONS`
- `NIM_CORS_ALLOW_HEADERS` — Default `Content-Type, Authorization, X-Request-Id, ...`

### Auth (for model downloads, not inference)
- `NGC_API_KEY` — NGC model download auth
- `HF_TOKEN` — HuggingFace model download auth

## Anthropic-Compatible `/v1/messages`
- NIM routes through nginx, no body rewriting
- No `x-api-key` validation (any non-empty string works)
- Supports: tool use, streaming (SSE with Anthropic event types)
- Extended thinking depends on model + vLLM version
- Batch/admin endpoints NOT supported
- No `anthropic-version` header enforcement

## Notes
- NIM API is backed by vLLM — full schema at `/docs` on the container
- This is for **self-hosted NIM containers** (not the public `integrate.api.nvidia.com` endpoint)
