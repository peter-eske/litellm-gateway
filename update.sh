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
docker compose pull
docker compose up -d

# Warten bis bereit
echo -n "Warte auf LiteLLM"
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:4000/health >/dev/null 2>&1; then
        echo " bereit"
        break
    fi
    echo -n "."
    sleep 2
done

# ── Verifikation ──
echo ""
echo ">> Verifikation"
echo -n "Health:   "
curl -sf http://127.0.0.1:4000/health | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('status','') in ('ok','healthy') else 'FEHLER')" \
    2>/dev/null || echo "FEHLER"

echo ""
echo "════════════════════════════════════════"
echo "  UPDATE FERTIG"
echo "════════════════════════════════════════"
