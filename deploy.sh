#!/bin/bash
# /www/wwwroot/gateway.ftbot.de/deploy.sh

set -euo pipefail

PROJECT_DIR="/www/wwwroot/gateway.ftbot.de"
EMAIL="admin@deine-domain.de"

# .env laden
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "[FEHLER] .env fehlt in $PROJECT_DIR"
    exit 1
fi
source "$PROJECT_DIR/.env"

echo "════════════════════════════════════════"
echo "  LiteLLM-Gateway Deployment"
echo "════════════════════════════════════════"

# ── 1. System Pakete ──
echo ""
echo ">> System"
apt-get update -qq
apt-get install -y -qq \
    nginx \
    certbot \
    python3-certbot-nginx \
    docker.io \
    docker-compose-plugin \
    curl

systemctl enable --now docker
systemctl enable --now nginx

# ── 2. Verzeichnisse ──
echo ""
echo ">> Verzeichnisse"
mkdir -p "$PROJECT_DIR/litellm_data"
mkdir -p "$PROJECT_DIR/nginx"
chmod 755 "$PROJECT_DIR/litellm_data"

# ── 3. TLS ──
echo ""
echo ">> TLS Zertifikat"
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    certbot certonly --nginx \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive
    echo "Zertifikat erstellt"
else
    echo "Zertifikat vorhanden"
fi

# ── 4. NGINX ──
echo ""
echo ">> NGINX"

# Domain einsetzen
sed "s/gateway\.ftbot\.de/$DOMAIN/g" \
    "$PROJECT_DIR/nginx/litellm-gateway.conf" \
    > /etc/nginx/sites-available/litellm-gateway

ln -sf /etc/nginx/sites-available/litellm-gateway \
       /etc/nginx/sites-enabled/litellm-gateway

rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx
echo "NGINX aktiv"

# ── 5. LiteLLM Container ──
echo ""
echo ">> LiteLLM Container"
cd "$PROJECT_DIR"

docker compose down 2>/dev/null || true
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

# ── 6. Virtual Key erstellen ──
echo ""
echo ">> Virtual Key für OpenCode"

# Prüfen ob Key schon existiert
EXISTING=$(curl -sf http://127.0.0.1:4000/key/list \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" 2>/dev/null || echo "")

if echo "$EXISTING" | grep -Fq "$OPENCODE_API_KEY" 2>/dev/null; then
    echo "Key existiert bereits"
else
    # Key mit 40 RPM Limit anlegen
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
        }" | python3 -m json.tool 2>/dev/null || echo "Key-Erstellung prüfen"
    echo "Key erstellt mit 40 RPM Limit"
fi

# ── 7. Verifikation ──
echo ""
echo ">> Verifikation"

echo -n "Health lokal:   "
curl -sf http://127.0.0.1:4000/health | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('status','') in ('ok','healthy') else 'FEHLER')" \
    2>/dev/null || echo "FEHLER"

echo -n "Models lokal:   "
curl -sf http://127.0.0.1:4000/v1/models \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(f'OK ({len(d[\"data\"])} Modelle)')" \
    2>/dev/null || echo "FEHLER"

echo -n "Health HTTPS:   "
curl -sf "https://$DOMAIN/health" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print('OK')" \
    2>/dev/null || echo "FEHLER - DNS/TLS prüfen"

# ── 8. Zusammenfassung ──
echo ""
echo "════════════════════════════════════════"
echo "  DEPLOYMENT FERTIG"
echo "════════════════════════════════════════"
echo ""
echo "  Endpunkt: https://$DOMAIN/v1"
echo "  Health:   https://$DOMAIN/health"
echo "  Models:   https://$DOMAIN/v1/models"
echo ""
echo "  LiteLLM UI (nur lokal via SSH Tunnel):"
echo "  ssh -L 4000:127.0.0.1:4000 root@$DOMAIN"
echo "  http://localhost:4000/ui"
echo ""
echo "  OpenCode lokal konfigurieren:"
echo ""
echo "  opencode.json:"
echo "  {"
echo "    \"\$schema\": \"https://opencode.ai/config.json\","
echo "    \"model\": \"opencode/nim-llama\","
echo "    \"provider\": {"
echo "      \"opencode\": {"
echo "        \"baseUrl\": \"https://$DOMAIN/v1\","
echo "        \"apiKey\": \"$OPENCODE_API_KEY\","
echo "        \"models\": {"
echo "          \"nim-llama\": {"
echo "            \"name\": \"NVIDIA NIM Llama 3.1 70B\""
echo "          }"
echo "        }"
echo "      }"
echo "    }"
echo "  }"
echo ""
echo "  Logs:"
echo "  docker compose -f $PROJECT_DIR/docker-compose.yml logs -f"
echo ""
echo "════════════════════════════════════════"