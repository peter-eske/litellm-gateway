# AGENTS.md — litellm-gateway

Single-Service LiteLLM-Deployment hinter NGINX, proxying 5 Modelle an die NVIDIA NIM API (Llama 3.3, DeepSeek V4 Pro, Phi-4-Mini, Qwen3-Coder-480B, DeepSeek V4 Flash). Läuft auf einem entfernten VPS unter `/www/wwwroot/gateway.ftbot.de/`.

## Architektur

```
OpenCode → HTTPS + Bearer → NGINX (TLS, Rate Limit) → LiteLLM (Docker, Port 4000) → NVIDIA NIM API
```

- LiteLLM-Container: Image von `docker.litellm.ai/berriai/litellm:main-latest`, Config per Volume-Mount, Container-Name `litellm-gateway`
- Port 4000 nur an `127.0.0.1` gebunden (kein öffentlicher Docker-Port)
- NGINX terminiert TLS, erzwingt Rate Limits (60r/m global, 10r/s API, 10 Verbindungen), handled Streaming
- LiteLLM-UI nur per SSH-Tunnel erreichbar: `ssh -L 4000:127.0.0.1:4000 root@$DOMAIN` → `http://localhost:4000/ui`
- PostgreSQL (16-alpine) als Sidecar für Key-Management und Persistenz

## Wichtige Dateien

| Datei | Zweck |
|---|---|
| `docker-compose.yml` | Zwei Services: `postgres` (16-alpine) + `litellm-gateway` (offizielles LiteLLM-Image), DB-Volume, Config per Volume-Mount |
| `litellm-config.yaml` | 5 Modell-Aliase (nim-llama→llama-3.3, default→deepseek-v4-pro, fast→phi-4-mini, power→qwen3-coder-480b, coding→deepseek-v4-flash) |
| `llm-toplist.md` | Rangliste Top-3 pro Rolle mit Benchmarks (aus good.json + bench.json) |
| `.env.example` | Erforderliche Variablen: `NVIDIA_API_KEY`, `LITELLM_MASTER_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `OPENCODE_API_KEY`, `DOMAIN` |
| `opencode.json.example` | OpenCode-Client-Konfiguration für das Gateway |

### Test-Skripte (universal, provider-agnostisch)

| Datei | Zweck |
|---|---|
| `scripts/config.json` | **Provider-Konfiguration** — API-Base-URL, Auth, Rate Limits, Timeouts pro Anbieter |
| `scripts/provider_api.py` | **Shared Library** — lädt Config, erzeugt OpenAI-Client, lädt Modelldaten |
| `scripts/phase1_quick_test.py` | **Phase 1**: 1-Token Health-Check aller Modelle (-> `phase1_results_{provider}.json`) |
| `scripts/test_models.py` | **Phase 2**: Streaming, Tool Calling, Max Output für OK-Modelle (-> `phase2_summary_{provider}.md`) |
| `scripts/known_specs_{provider}.json` | **Modell-Metadaten** pro Provider (Parameter, Context, Typ) |
| `scripts/bench.json` | **Benchmark-Daten** (45 Benchmarks, 438 Modelle aus Scale AI + swebench.com + SWE-bench Pro) |
| `scripts/fetch_scale_leaderboard.py` | Extrahiert 38 Benchmarks aus dem Scale AI Leaderboard (RSC Payload) |
| `scripts/fetch_swebench.py` | Extrahiert 6 SWE-bench Leaderboards (Verified, bash-only, Multilingual, etc.) |
| `scripts/rank_models.py` | Rangliste Top-3 pro OpenCode-Alias aus good.json |
| `scripts/update_benchmarks_in_good.py` | Merged bench.json → good.json |
| `scripts/restore_lost_benchmarks.py` | Stellt alte Benchmark-Daten wieder her |

### NVIDIA NIM spezifisch

| Datei | Zweck |
|---|---|
| `scripts/NIM_API_REFERENCE.md` | NVIDIA NIM API Referenz (Endpoints, Env Vars) |
| `scripts/NIM_FAILURE_LOG.md` | Log aller 404/410/Timeout Modelle |
| `scripts/phase1_results.json` | Phase 1 NVIDIA Ergebnisse (Legacy) |
| `scripts/phase1_results_nvidia-nim.json` | Phase 1 NVIDIA Ergebnisse (neues Format) |

## Script Usage

```bash
# Phase 1: Health-Check aller Modelle
$env:NVIDIA_API_KEY = "nvapi-..."
python scripts/phase1_quick_test.py --provider nvidia-nim

# Phase 2: Detailtests (nur OK-Modelle)
python scripts/test_models.py --provider nvidia-nim
```

Bei neuem Provider: `config.json` erweitern, `known_specs_{provider}.json` anlegen, `--provider name` übergeben.

## OpenCode Skill: API Error Handling

Ein permanenter Skill unter `~/.config/opencode/skills/api-error-handling/SKILL.md`
dokumentiert die HTTP-Fehlerklassifikation für KI-APIs. Enthält:
- Bedeutung von 404, 401, 403, 429, 500
- `openai`-Exception-Hierarchie (NotFoundError, RateLimitError, etc.)
- Python-Codebeispiele für try-except, Model-Liste, Raw-Response-Header

## Verifikation

```bash
curl -s https://$DOMAIN/health
curl -s https://$DOMAIN/v1/chat/completions \
  -H "Authorization: Bearer $OPENCODE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"nim-llama","messages":[{"role":"user","content":"Test"}]}'
# Teste weitere Aliase: default, fast, power, coding
```

## Container-Neustart

```bash
docker compose -f /www/wwwroot/gateway.ftbot.de/docker-compose.yml down
docker compose -f /www/wwwroot/gateway.ftbot.de/docker-compose.yml up -d
docker compose -f /www/wwwroot/gateway.ftbot.de/docker-compose.yml logs -f
```

## Fallstricke

- `docker.litellm.ai` erlaubt anonyme Pulls (kein Login nötig)
- Alle Skripte nutzen die `openai`-Bibliothek (v2.x) statt `urllib` — muss installiert sein: `pip install openai`
- `openai`-Exception-Hierarchie: `APIError` → `APIStatusError` (404=NotFoundError, 429=RateLimitError, etc.), `APITimeoutError`, `APIConnectionError`
- Rate-Limit-Header via `client.with_raw_response.chat.completions.create(...)` → `raw.headers`

## CI/CD (GitHub Actions)

Bei Push auf `main` führt der Workflow `.github/workflows/deploy.yml` einen Job aus:

1. **`deploy`** – Per SSH auf den VPS: git pull, `.env` laden, Container neustarten, Virtual Key anlegen, Verifikation

Kein eigener Image-Build mehr – die Config wird per Volume-Mount bereitgestellt, das Image kommt direkt von `docker.litellm.ai/berriai/litellm:main-latest`.

### Erforderliche GitHub Secrets (Org-Ebene Eske-IT)

Organisation-Secrets unter `https://github.com/organizations/Eske-IT/settings/secrets/actions`. Siehe `.github/SECRETS.md` für Details.

| Secret | Beschreibung |
|---|---|
| `SSH_HOST` | `213.202.218.154` |
| `SSH_USER` | `root` |
| `SSH_KEY` | Privater SSH-Key (via `ssh-keygen -t ed25519`) |
| `SSH_PORT` | `22` |

Den Public-Key auf dem VPS autorisieren: `ssh-copy-id root@213.202.218.154`

- `.env` **muss** unter `/www/wwwroot/gateway.ftbot.de/.env` existieren, sonst bricht der Workflow ab
- Docker healthcheck nutzt `/health/liveliness` (kein Auth, kein DB nötig) – nicht `/health` (braucht DB + Auth)
- `public_endpoints: ["/health", "/health/liveliness"]` in `litellm-config.yaml`
- Keine deploy-Limits (512M + healthcheck-Fails verursachten OOM exit 137)
- Config wird per Volume-Mount in `docker-compose.yml` bereitgestellt (kein eigener Image-Build)
- Keine Retries (`num_retries: 0`), kein Redis, keine Telemetrie
- PostgreSQL (16-alpine) für Key-Management – `DATABASE_URL` via Environment
- Virtual Key `sk-opencode-...` wird im Workflow automatisch via API angelegt
- aaPanel NGINX-Config patcht der Workflow automatisch: `https://localhost:4000` → `http://127.0.0.1:4000`, `Host localhost` → `Host $host`, + streaming
- `plan.md` wurde gelöscht — alle relevanten Informationen sind in dieser `AGENTS.md` enthalten
