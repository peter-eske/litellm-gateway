#!/bin/bash
# /www/wwwroot/gateway.ftbot.de/update.sh
# Wird von GitHub Actions per SSH auf dem VPS ausgeführt.
# Führt nur Update-Schritte aus, kein initiales Deployment.

set -euo pipefail

PROJECT_DIR="/www/wwwroot/gateway.ftbot.de"

echo "════════════════════════════════════════"
echo "  LiteLLM-Gateway Update"
echo "════════════════════════════════════════"

# ── Repo updaten ──
echo ""
echo ">> Git Pull"
cd "$PROJECT_DIR"
git pull

# ── .env laden ──
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "[FEHLER] .env fehlt in $PROJECT_DIR"
    exit 1
fi
source "$PROJECT_DIR/.env"

# ── NGINX Config (nur wenn geändert) ──
if git diff HEAD@{1} HEAD --name-only --relative="$PROJECT_DIR" 2>/dev/null | grep -q "^nginx/litellm-gateway.conf"; then
    echo ""
    echo ">> NGINX Config geändert → lade neu"
    sed "s/gateway\.ftbot\.de/$DOMAIN/g" \
        "$PROJECT_DIR/nginx/litellm-gateway.conf" \
        > /etc/nginx/sites-available/litellm-gateway
    nginx -t
    systemctl reload nginx
    echo "NGINK neu geladen"
else
    echo ">> NGINX Config unverändert"
fi

# ── Container neustarten ──
echo ""
echo ">> Docker Container"

# Alten manuell gestarteten Container entfernen (falls vorhanden)
docker rm -f litellm-gateway 2>/dev/null || true

docker compose pull
docker compose up -d

# Warten bis bereit
echo -n "Warte auf LiteLLM"
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:4000/health/liveliness >/dev/null 2>&1; then
        echo " bereit"
        break
    fi
    echo -n "."
    sleep 2
done

# ── Virtual Key anlegen (falls nicht vorhanden) ──
echo ""
echo ">> Virtual Key für OpenCode"
EXISTING=$(curl -sf http://127.0.0.1:4000/key/list \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" 2>/dev/null || echo "")
if echo "$EXISTING" | grep -Fq "$OPENCODE_API_KEY" 2>/dev/null; then
    echo "Key existiert bereits"
else
    curl -sf -X POST http://127.0.0.1:4000/key/generate \
        -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"key\": \"$OPENCODE_API_KEY\",
            \"models\": [\"nim-llama\", \"default\"],
            \"rpm_limit\": 40,
            \"tpm_limit\": 1000000,
            \"max_parallel_requests\": 1,
            \"metadata\": {
                \"description\": \"OpenCode Gateway Key\",
                \"min_delay_ms\": 2100
            }
        }" >/dev/null 2>&1 && echo "Key erstellt mit 40 RPM Limit" || echo "Key-Erstellung fehlgeschlagen"
fi

# ── Verifikation ──
echo ""
echo ">> Verifikation"
echo -n "Health Liveliness: "
curl -sf http://127.0.0.1:4000/health/liveliness >/dev/null 2>&1 && echo "OK" || echo "FEHLER"

echo ""
echo "════════════════════════════════════════"
echo "  UPDATE FERTIG"
echo "════════════════════════════════════════"
