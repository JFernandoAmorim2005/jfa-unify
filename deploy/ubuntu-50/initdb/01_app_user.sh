#!/bin/bash
# Executado pelo container PostgreSQL na primeira inicialização (initdb).
# Cria o role app_user. PASSWORD vem de POSTGRES_APP_USER_PASSWORD (definida no .env).
set -e

APP_USER_PASSWORD="${POSTGRES_APP_USER_PASSWORD:-changeme-set-in-env}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER app_user WITH PASSWORD '${APP_USER_PASSWORD}' NOSUPERUSER NOBYPASSRLS;
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO app_user;
    GRANT USAGE ON SCHEMA public TO app_user;
EOSQL

echo "app_user criado com sucesso."
