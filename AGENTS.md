# AGENTS.md — litellm-gateway

Single-Service LiteLLM-Deployment hinter NGINX, proxying an die NVIDIA NIM API (Llama 3.1 70B). Läuft auf einem entfernten VPS unter `/www/wwwroot/gateway.ftbot.de/`.

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
| `litellm-config.yaml` | 2 Modell-Aliase (`nim-llama`, `default`) → NVIDIA NIM; keine Retries, keine Telemetrie, lokale Queue |
| `.env.example` | Erforderliche Variablen: `NVIDIA_API_KEY`, `LITELLM_MASTER_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `OPENCODE_API_KEY`, `DOMAIN` |
| `opencode.json.example` | OpenCode-Client-Konfiguration für das Gateway |

## Verifikation

```bash
curl -s https://$DOMAIN/health
curl -s https://$DOMAIN/v1/chat/completions \
  -H "Authorization: Bearer $OPENCODE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"nim-llama","messages":[{"role":"user","content":"Test"}]}'
```

## Container-Neustart

```bash
docker compose -f /www/wwwroot/gateway.ftbot.de/docker-compose.yml down
docker compose -f /www/wwwroot/gateway.ftbot.de/docker-compose.yml up -d
docker compose -f /www/wwwroot/gateway.ftbot.de/docker-compose.yml logs -f
```

## Fallstricke

- `docker.litellm.ai` erlaubt anonyme Pulls (kein Login nötig)

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
