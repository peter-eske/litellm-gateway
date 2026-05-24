# Plan (veraltet)

**Diese Datei ist veraltet.** Alle Informationen sind in `AGENTS.md` enthalten.

## Ursprüngliche Architektur

```
OpenCode (lokal)
  │
  │  HTTPS + Bearer ngw-xxxx
  ▼
NGINX (VPS)
  │  TLS Termination
  │  Rate Limit
  │  proxy_pass 127.0.0.1:4000
  ▼
LiteLLM (Docker)
  │  Master Key Auth
  │  Virtual Key Auth (ngw-xxxx)
  │  40 RPM Hard Limit pro Key
  │  Request Queue (lokal, kein Redis)
  │  OpenAI Schema Wrapper
  ▼
NVIDIA NIM API
```

## Ursprüngliche Verzeichnisstruktur

```
/www/wwwroot/gateway.ftbot.de/
├── docker-compose.yml
├── litellm-config.yaml
├── nginx/
│   ├── litellm-gateway.conf
│   └── ip-whitelist.conf
├── litellm_data/      # SQLite + persistente Daten
└── .env
```

## Ursprüngliche Deployment-Schritte

```bash
# 1. Dateien auf VPS kopieren
scp -r . root@dein-vps:/www/wwwroot/gateway.ftbot.de/

# 2. .env anpassen
ssh root@dein-vps
nano /www/wwwroot/gateway.ftbot.de/.env

# 3. Ausführen
chmod +x /www/wwwroot/gateway.ftbot.de/deploy.sh
/www/wwwroot/gateway.ftbot.de/deploy.sh

# 4. Testen
curl -s https://gateway.ftbot.de/health

curl -s https://gateway.ftbot.de/v1/chat/completions \
  -H "Authorization: Bearer sk-opencode-dein-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nim-llama",
    "messages": [{"role": "user", "content": "Test"}]
  }'

# 5. LiteLLM UI (SSH Tunnel)
ssh -L 4000:127.0.0.1:4000 root@dein-vps
# Browser: http://localhost:4000/ui
```
