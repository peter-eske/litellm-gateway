# OpenCode-Verbindung zum Gateway

## Voraussetzung

Das Gateway muss live sein unter `https://gateway.ftbot.de`.

## Verbindung lokal einrichten

### Schritt 1: `opencode.json` konfigurieren

Datei: `C:\Users\peter\.config\opencode\opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/nim-llama",
  "provider": {
    "opencode": {
      "baseUrl": "https://gateway.ftbot.de/v1",
      "apiKey": "sk-opencode-min-32-zeichen-hier-eintragen",
      "models": {
        "nim-llama": {
          "name": "NVIDIA Llama 3.3 70B (Legacy)"
        },
        "default": {
          "name": "NVIDIA DeepSeek V4 Pro (Allrounder)"
        },
        "fast": {
          "name": "NVIDIA Phi-4-Mini 3.8B (Low Latency)"
        },
        "power": {
          "name": "NVIDIA Qwen3-Coder 480B (Max Quality)"
        },
        "coding": {
          "name": "NVIDIA DeepSeek V4 Flash (Code)"
        }
      }
    }
  }
}
```

### Schritt 2: Prüfen

```bash
curl -s https://gateway.ftbot.de/v1/chat/completions \
  -H "Authorization: Bearer sk-opencode-min-32-zeichen-hier-eintragen" \
  -H "Content-Type: application/json" \
  -d '{"model":"nim-llama","messages":[{"role":"user","content":"Hallo"}]}'
```

Weitere Aliase testen: `"model":"default"`, `"model":"fast"`, `"model":"power"`, `"model":"coding"`.

## Gateway-Neustart (falls nötig)

```bash
ssh peter@213.202.218.154
cd /www/wwwroot/gateway.ftbot.de
docker compose down
docker compose up -d
```

## Nützliche Befehle

| Befehl | Zweck |
|---|---|
| `curl https://gateway.ftbot.de/health/liveliness` | Health-Check (öffentlich) |
| `curl -H "Authorization: Bearer \$LITELLM_MASTER_KEY" https://gateway.ftbot.de/v1/models` | Modelle auflisten |
| `ssh -L 4000:127.0.0.1:4000 peter@213.202.218.154` | SSH-Tunnel für LiteLLM UI |
| `http://localhost:4000/ui` | LiteLLM UI (nur via Tunnel) |
