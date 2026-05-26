# AGENTS.md — litellm-gateway

Single LiteLLM behind NGINX, proxying 8 model aliases to NVIDIA NIM. Deployed on VPS `213.202.218.154`.

```
HTTPS + Bearer → NGINX (TLS) → LiteLLM (:4000) → NVIDIA NIM API
                                    └→ Debate-Server (:8000, /debate/sse)
```

## Model Aliases

All use `api_base: https://integrate.api.nvidia.com/v1`, `num_retries: 0`. Config in `litellm-config.yaml`. Note `openai/` prefix in model names (LiteLLM convention for OpenAI-compatible endpoints).

| Alias | Model | Temp | Max Tokens | Timeout | Stream | Tools |
|---|---|---|---|---|---|---|
| `nim-llama` | `meta/llama-3.3-70b-instruct` | 0.2 | 4096 | 180s | ✅ | ✅ |
| `default` | `deepseek-ai/deepseek-v4-flash` | 0.2 | 8192 | 300s | ✅ | ✅ |
| `fast` | `mistralai/ministral-14b-instruct-2512` | 0.5 | 4096 | 60s | ✅ | ✅ |
| `power` | `mistralai/mistral-large-3-675b-instruct-2512` | 0.2 | 8192 | 300s | ✅ | ✅ |
| `coding` | `openai/gpt-oss-120b` | 0.1 | 8192 | 180s | ✅ | ✅ |
| `reasoning` | `deepseek-ai/deepseek-v4-pro` | 0.2 | 8192 | 300s | ✅ | ❌ |
| `vision` | `meta/llama-3.2-90b-vision-instruct` | 0.2 | 4096 | 180s | ✅ | ✅ |
| `safety` | `nvidia/llama-3.1-nemoguard-8b-content-safety` | 0.1 | 512 | 30s | ✅ | ❌ |

`nim-llama` has `top_p:0.7`. `power` replaces the original `qwen3-coder-480b` which had no streaming support on NIM. `safety` is a content guard only (no tools/chats). Benchmarks per alias in `llm-toplist.md`.

## Configuration Reference

- **Env vars** (`.env` required, see `.env.example`): `NVIDIA_API_KEY`, `LITELLM_MASTER_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `OPENCODE_API_KEY`, `POSTGRES_PASSWORD`, `DOMAIN`
- **Infra**: `docker-compose.yml` (3 services: postgres, litellm-gateway, debate-server)
- **LiteLLM image**: `docker.litellm.ai/berriai/litellm:main-latest` (anonymous pull)
- **OpenCode client**: `opencode.json.example` / `opencode.md`
- **Debate-server**: built from `github.com/peter-eske/MCP-Server-Tools`, exposed at `/debate/sse`
- Port 4000 bound to `127.0.0.1` only (no public Docker port)
- Healthcheck: `/health/liveliness` (no auth). `/health` requires DB + auth
- DB: PostgreSQL 16-alpine sidecar for key management
- LiteLLM queue: local, 60s timeout, `routing_strategy: "simple-shuffle"`
- NGINX `proxy_read_timeout 300s` (must exceed LiteLLM's 60s queue timeout)

## Deployment (push to `main` → GitHub Actions)

Workflow in `.github/workflows/deploy.yml` (secrets: `SSH_HOST`, `SSH_USER`, `SSH_KEY`, `SSH_PORT`):
1. `git fetch origin && git reset --hard origin/main`
2. Source `.env` at project root (fails if missing)
3. Patch aaPanel NGINX config (streaming, 300s timeouts, `/debate/` location)
4. `docker rm -f litellm-gateway`, `docker compose pull`, `docker compose build debate-server`, `docker compose up -d`
5. Wait for `/health/liveliness` (30×2s retries)
6. Delete old `sk-opencode-*` key, recreate with all 8 models (40 RPM, 2.1s min delay)
7. Verify debate-server SSE endpoints

## SSH & Container Management

```bash
ssh peter@213.202.218.154
cd /www/wwwroot/gateway.ftbot.de
docker compose logs -f
docker compose down && docker compose up -d
ssh -L 4000:127.0.0.1:4000 peter@213.202.218.154   # tunnel → http://localhost:4000/ui
```

## Scripts Pipeline

Test scripts under `scripts/`, provider-agnostic, using `openai` v2.x SDK. Config: `scripts/config.json` (20 RPM, 3s delay).

```powershell
pip install openai
$env:NVIDIA_API_KEY = "nvapi-..."
python scripts/phase1_quick_test.py --provider nvidia-nim   # health + 404 detection
python scripts/test_models.py --provider nvidia-nim          # stream/tool/max_out test
python scripts/update_benchmarks_in_good.py                  # bench.json → good.json
python scripts/rank_models.py                                # top-3 per alias
```

Data: `scripts/good.json` (113 models), `scripts/bench.json` (45 sources, 438 models). 404/timeout models auto-ignored in `scripts/ignore.json`.

## Verification

```bash
curl -s https://gateway.ftbot.de/health/liveliness            # "I'm alive!"
curl -s https://gateway.ftbot.de/v1/chat/completions \
  -H "Authorization: Bearer $OPENCODE_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"nim-llama","messages":[{"role":"user","content":"Test"}]}'
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" https://gateway.ftbot.de/v1/models
```

## Notes

- This repo is pure infra config + CI + Python scripts. No local dev server.
- `clean-old-winget.ps1` is unrelated to the gateway — ignore it.
