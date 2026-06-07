#!/usr/bin/env bash
# Deploy JFA_Unify Ubuntu .50 — clone + build + up + smoke test
#
# Instalar (PRIMEIRA vez — uma única vez):
#   gh repo clone JFernandoAmorim2005/jfa-unify /tmp/jfa-unify-install
#   sudo cp /tmp/jfa-unify-install/deploy/ubuntu-50/deploy-unify.sh /usr/local/bin/deploy-unify
#   sudo chmod +x /usr/local/bin/deploy-unify
#   rm -rf /tmp/jfa-unify-install
#   hash -r
#   sudo mkdir -p /opt/jfa-unify
#   sudo chown $USER:$USER /opt/jfa-unify
#
# PRÉ-REQUISITOS (FA fazer manualmente antes do 1.º deploy):
#   1. Criar /opt/jfa-unify/.env a partir de deploy/ubuntu-50/.env.example (preencher secrets)
#   2. Cloudflare Zero Trust → Networks → Tunnels → accesspay-ubuntu → Public Hostname:
#      unify.jfernandoamorim.com → http://localhost:8043
#
# Uso (dia-a-dia — auto-actualiza o script em cada deploy):
#   deploy-unify

set -euo pipefail

REPO="https://github.com/JFernandoAmorim2005/jfa-unify.git"
CLONE_DIR="/tmp/jfa-unify-deploy-$$"
APP_DIR="/opt/jfa-unify"
CONTAINER="jfa-unify"
PORT=8043

log() { echo -e "[deploy-unify] $*"; }

# --- 1. Clone ---
log "clone..."
rm -rf "$CLONE_DIR"
if command -v gh >/dev/null 2>&1; then
    sudo -u famorim -H gh repo clone JFernandoAmorim2005/jfa-unify "$CLONE_DIR" -- --depth 1
    chown -R "$(id -u):$(id -g)" "$CLONE_DIR" 2>/dev/null || true
else
    log "ERRO: gh CLI nao instalado. Instalar: sudo apt install -y gh && gh auth login --web"
    exit 1
fi
cd "$CLONE_DIR"
HEAD=$(git rev-parse --short HEAD)
log "HEAD $HEAD"

# --- 2. Ensure APP_DIR ---
mkdir -p "$APP_DIR/postgres/data" "$APP_DIR/mosquitto/data" "$APP_DIR/data"

# Primeira vez: copiar .env.example se .env nao existir
if [ ! -f "$APP_DIR/.env" ]; then
    log "WARN: $APP_DIR/.env nao existe, a copiar .env.example"
    cp "$CLONE_DIR/deploy/ubuntu-50/.env.example" "$APP_DIR/.env"
    log ">>> PREENCHER $APP_DIR/.env com secrets antes de continuar"
    log ">>> Especialmente: POSTGRES_PASSWORD, POSTGRES_APP_USER_PASSWORD, SECRET_KEY"
    exit 1
fi

# --- 3. rsync sources ---
log "rsync sources -> $APP_DIR/src"
rsync -a --delete \
    --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.venv' --exclude='test.db' --exclude='.env' \
    "$CLONE_DIR/" "$APP_DIR/src/"

cd "$APP_DIR/src"

# --- 4. Build ---
log "docker compose build..."
docker compose -f deploy/ubuntu-50/docker-compose.prod.yml build

# --- 5. Arrancar infra (postgres, redis, mosquitto) ---
log "docker compose up -d (infra)..."
docker rm -f "$CONTAINER" 2>/dev/null || true
docker compose -f deploy/ubuntu-50/docker-compose.prod.yml up -d postgres redis mosquitto

log "aguardar PostgreSQL healthy..."
for i in {1..20}; do
    if docker inspect --format='{{.State.Health.Status}}' unify-postgres 2>/dev/null | grep -q "healthy"; then
        log "postgres healthy"
        break
    fi
    sleep 3
done

# --- 6. Alembic upgrade head ---
log "alembic upgrade head..."
if ! docker compose -f deploy/ubuntu-50/docker-compose.prod.yml run --rm api \
    alembic -c alembic.ini upgrade head; then
    log "ERRO alembic upgrade falhou — abortar deploy"
    exit 1
fi

# --- 7. Grants app_user (após tabelas criadas pelo Alembic) ---
log "grants app_user..."
docker exec unify-postgres psql -U jfaunify -d jfaunify <<-EOSQL
    GRANT SELECT, INSERT, UPDATE, DELETE ON tenants TO app_user;
    GRANT SELECT, INSERT, UPDATE, DELETE ON input_devices TO app_user;
    GRANT SELECT, INSERT, UPDATE, DELETE ON access_logs TO app_user;
    GRANT SELECT, INSERT, UPDATE, DELETE ON mqtt_topic_mappings TO app_user;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO app_user;
EOSQL

# --- 8. API up ---
log "docker compose up -d (api)..."
docker compose -f deploy/ubuntu-50/docker-compose.prod.yml up -d --force-recreate api

# --- 9. Smoke test ---
log "smoke test /health (10 tentativas)..."
for i in {1..10}; do
    if curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1; then
        log "health OK"
        curl -s "http://localhost:${PORT}/health" | head -c 200
        echo
        break
    fi
    sleep 3
done

if ! curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1; then
    log "ERRO: health check falhou apos 10 tentativas"
    docker logs --tail 50 "$CONTAINER" 2>&1 || true
    exit 1
fi

log "alembic current (diagnostico)..."
docker exec "$CONTAINER" alembic -c alembic.ini current 2>&1 | sed "s/^/[alembic] /" || \
    log "WARN: alembic current falhou"

# --- 10. Auto-update script ---
SELF=$(command -v deploy-unify 2>/dev/null || true)
NEW_SELF="$APP_DIR/src/deploy/ubuntu-50/deploy-unify.sh"
if [ -n "$SELF" ] && [ -f "$NEW_SELF" ]; then
    if cp "$NEW_SELF" "$SELF" 2>/dev/null && chmod +x "$SELF"; then
        log "deploy-unify auto-updated -> $SELF"
    else
        log "WARN: auto-update falhou — correr manualmente: sudo cp $NEW_SELF /usr/local/bin/deploy-unify"
    fi
fi

# --- 11. Cleanup ---
rm -rf "$CLONE_DIR"
log "=== DONE ($HEAD) ==="
