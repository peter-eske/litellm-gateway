# AGENTS.md — litellm-gateway

Single-Service LiteLLM-Deployment hinter NGINX, proxying an die NVIDIA NIM API (Llama 3.1 70B). Läuft auf einem entfernten VPS unter `/www/wwwroot/gateway.ftbot.de/`.

## Architektur

```
OpenCode → HTTPS + Bearer → NGINX (TLS, Rate Limit) → LiteLLM (Docker, Port 4000) → NVIDIA NIM API
```

- LiteLLM-Container: `ghcr.io/berriai/litellm:main-latest`, Container-Name `litellm-gateway`
- Port 4000 nur an `127.0.0.1` gebunden (kein öffentlicher Docker-Port)
- NGINX terminiert TLS, erzwingt Rate Limits (60r/m global, 10r/s API, 10 Verbindungen), handled Streaming
- LiteLLM-UI nur per SSH-Tunnel erreichbar: `ssh -L 4000:127.0.0.1:4000 root@$DOMAIN` → `http://localhost:4000/ui`

## Wichtige Dateien

| Datei | Zweck |
|---|---|
| `docker-compose.yml` | Einzelner `litellm-gateway`-Service, keine Abhängigkeiten |
| `litellm-config.yaml` | 2 Modell-Aliase (`nim-llama`, `default`) → NVIDIA NIM; keine Retries, keine Telemetrie, lokale Queue |
| `nginx/litellm-gateway.conf` | TLS, Rate Limits, Streaming-Konfiguration (`proxy_buffering off`) |
| `deploy.sh` | Vollständiges Deployment: Systempakete → certbot TLS → NGINX → Docker → Virtual Key → Verifikation |
| `.env.example` | Erforderliche Variablen: `NVIDIA_API_KEY`, `LITELLM_MASTER_KEY`, `UI_USERNAME`, `UI_PASSWORD`, `OPENCODE_API_KEY`, `DOMAIN` |
| `opencode.json.example` | OpenCode-Client-Konfiguration für das Gateway |

## Deployment-Befehle

```bash
# Auf VPS kopieren
scp -r . root@deine-vps:/www/wwwroot/gateway.ftbot.de/

# Per SSH einloggen, .env erstellen, dann deployen
ssh root@deine-vps
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

- `.env` **muss** unter `/www/wwwroot/gateway.ftbot.de/.env` existieren bevor `deploy.sh` läuft, sonst bricht das Skript ab
- `deploy.sh` verwendet `docker compose` (v2 Plugin), nicht das standalone `docker-compose`
- `deploy.sh` bindet `.env` direkt via `source` ein — Shell expandiert env vars inline
- `EMAIL`-Variable in `deploy.sh` (Zeile 7, `admin@deine-domain.de`) muss vor dem ersten Deployment angepasst werden
- `sed` ersetzt `gateway.ftbot.de` im nginx-Config zur Deployment-Zeit (Platzhalter ist hartkodiert)
- Container gecappt auf 0,4 Kerne, 512 MB RAM
- SQLite-DB unter `litellm_data/litellm.db` — keine externe Datenbank
- Keine Retries (`num_retries: 0`), kein Redis, keine Telemetrie
- `plan.md` ist veraltet — alle relevanten Informationen sind in dieser `AGENTS.md` enthalten
