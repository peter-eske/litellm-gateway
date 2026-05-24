# AGENTS.md — litellm-gateway

Single-Service LiteLLM-Deployment hinter NGINX, proxying an die NVIDIA NIM API (Llama 3.1 70B). Läuft auf einem entfernten VPS unter `/www/wwwroot/gateway.ftbot.de/`.

## Architektur

```
OpenCode → HTTPS + Bearer → NGINX (TLS, Rate Limit) → LiteLLM (Docker, Port 4000) → NVIDIA NIM API
```

- LiteLLM-Container: Eigenes GHCR-Image `ghcr.io/peter-eske/litellm-gateway:latest`, gebaut aus `Dockerfile` (basiert auf `litellm/litellm:main-stable`), Container-Name `litellm-gateway`
- Port 4000 nur an `127.0.0.1` gebunden (kein öffentlicher Docker-Port)
- NGINX terminiert TLS, erzwingt Rate Limits (60r/m global, 10r/s API, 10 Verbindungen), handled Streaming
- LiteLLM-UI nur per SSH-Tunnel erreichbar: `ssh -L 4000:127.0.0.1:4000 root@$DOMAIN` → `http://localhost:4000/ui`

## Wichtige Dateien

| Datei | Zweck |
|---|---|
| `Dockerfile` | Baut eigenes Image basierend auf `litellm/litellm:main-stable`, Config embedded |
| `docker-compose.yml` | Einzelner `litellm-gateway`-Service, zieht GHCR-Image, kein Config-Volume |
| `litellm-config.yaml` | 2 Modell-Aliase (`nim-llama`, `default`) → NVIDIA NIM; keine Retries, keine Telemetrie, lokale Queue |
| `nginx/litellm-gateway.conf` | TLS, Rate Limits, Streaming-Konfiguration (`proxy_buffering off`) |
| `deploy.sh` | Vollständiges Deployment: Systempakete → certbot TLS → NGINX → Docker → Virtual Key → Verifikation |
| `.env.example` | Erforderliche Variablen: `NVIDIA_API_KEY`, `LITELLM_MASTER_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `OPENCODE_API_KEY`, `DOMAIN` |
| `opencode.json.example` | OpenCode-Client-Konfiguration für das Gateway |

## Deployment-Befehle

```bash
# Auf VPS kopieren
scp -r . root@213.202.218.154:/www/wwwroot/gateway.ftbot.de/

# Per SSH einloggen, .env erstellen, dann deployen
ssh root@213.202.218.154
chmod +x /www/wwwroot/gateway.ftbot.de/deploy.sh
/www/wwwroot/gateway.ftbot.de/deploy.sh
```

`deploy.sh` erstellt automatisch einen Virtual Key (40 RPM-Limit) über die LiteLLM-API beim ersten Durchlauf.

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

- GHCR (`ghcr.io/berriai/litellm`) verweigert anonyme Pulls → Ausweichen auf Docker Hub (`litellm/litellm`)

## CI/CD (GitHub Actions)

Bei Push auf `main` durchläuft der Workflow `.github/workflows/deploy.yml` zwei Jobs:

1. **`build`** – Baut das Docker-Image via `Dockerfile` und pusht es an `ghcr.io/peter-eske/litellm-gateway:latest` (nutzt `GITHUB_TOKEN`)
2. **`deploy`** (braucht `build`) – Per SSH auf den VPS: git pull, dann `update.sh` (docker compose pull + up -d)

### Erforderliche GitHub Secrets (Org-Ebene Eske-IT)

Organisation-Secrets unter `https://github.com/organizations/Eske-IT/settings/secrets/actions`. Siehe `.github/SECRETS.md` für Details.

| Secret | Beschreibung |
|---|---|
| `SSH_HOST` | `213.202.218.154` |
| `SSH_USER` | `root` |
| `SSH_KEY` | Privater SSH-Key (via `ssh-keygen -t ed25519`) |
| `SSH_PORT` | `22` |

Den Public-Key auf dem VPS autorisieren: `ssh-copy-id root@213.202.218.154`

- `.env` **muss** unter `/www/wwwroot/gateway.ftbot.de/.env` existieren bevor `deploy.sh` läuft, sonst bricht das Skript ab
- `deploy.sh` verwendet `docker compose` (v2 Plugin), nicht das standalone `docker-compose`
- `deploy.sh` bindet `.env` direkt via `source` ein — Shell expandiert env vars inline
- `EMAIL`-Variable in `deploy.sh` (Zeile 7, `admin@deine-domain.de`) muss vor dem ersten Deployment angepasst werden
- `sed` ersetzt `gateway.ftbot.de` im nginx-Config zur Deployment-Zeit (Platzhalter ist hartkodiert)
- Docker healthcheck nutzt `/health/liveliness` (kein Auth, kein DB nötig) – nicht `/health` (braucht DB + Auth)
- `public_endpoints: ["/health", "/health/liveliness"]` in `litellm-config.yaml`
- Keine deploy-Limits (512M + healthcheck-Fails verursachten OOM exit 137)
- Config in Dockerfile embedded (kein Volume-Mount für `litellm-config.yaml`)
- Keine Retries (`num_retries: 0`), kein Redis, keine Telemetrie
- `plan.md` ist veraltet — alle relevanten Informationen sind in dieser `AGENTS.md` enthalten
