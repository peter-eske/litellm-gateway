# Local Proxy Test Report

**Date:** 2026-05-26
**Proxy:** `http://localhost:4000`

## Results

| Model | Alias | Chat | Stream | Tools | Latency (chat) |
|---|---|---|---|---|---|
| `deepseek-ai/deepseek-v4-flash` | `default` | ✅ | ✅ | ✅ | 10.7s |
| `meta/llama-3.3-70b-instruct` | `nim-llama` | ✅ | ✅ | ✅ | 1.0s |
| `mistralai/ministral-14b-instruct-2512` | `fast` | ✅ | ✅ | ✅ | 0.3s |
| `qwen/qwen3-coder-480b-a35b-instruct` | `power` | ✅ | ✅ | ✅ | 8.0s |
| `openai/gpt-oss-120b` | `coding` | ✅ | ✅ | ✅ | 0.5s |
| `deepseek-ai/deepseek-v4-pro` | `reasoning` | ✅ | ✅ | ✅ | 21.1s |
| `meta/llama-3.2-90b-vision-instruct` | `vision` | ✅ | ✅ | ✅ | 0.6s |
| `nvidia/llama-3.1-nemoguard-8b-content-safety` | `safety` | ✅ | ✅ | N/A* | 0.2s |

*\* Content safety guard doesn't support tool calling by design.*

## Issues Fixed

1. **Privoxy Proxy** — OpenAI SDK used system proxy (httpx auto-detection). Fixed with `NO_PROXY=*`.
2. **401 Unauthorized** — Fresh DB had no registered `OPENCODE_API_KEY`. Fixed by using `LITELLM_MASTER_KEY`.
3. **`default` timeout** — 180s was too short for NVIDIA cold start. Increased to 300s.
4. **`coding` NoneType** — Response parsing was fragile. Added `getattr` guards.

## Cold Start Observations

- `power` (qwen3-coder-480b): ~22s cold start, subsequent calls faster
- `default` (deepseek-v4-flash): ~10s warm, ~180s if cold
- `reasoning` (deepseek-v4-pro): ~21s first call
