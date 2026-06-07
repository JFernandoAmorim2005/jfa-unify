-- Setup PostgreSQL RLS para testes de integração JFA
-- Executar como superuser (postgres)

-- 1. Criar database de teste
CREATE DATABASE jfa_test ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C' TEMPLATE template0;
\c jfa_test

-- 2. Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 3. Criar schema
CREATE SCHEMA IF NOT EXISTS public;

-- 4. Criar user app_user com restrições RLS
CREATE USER app_user WITH PASSWORD 'test-app-password' NOSUPERUSER NOBYPASSRLS;

-- 5. Tabelas base (mimic das migrações Alembic)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE input_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    pin_salt BYTEA NOT NULL,
    mqtt_topic VARCHAR(255) NOT NULL,
    pin_hash_algorithm VARCHAR(50) DEFAULT 'bcrypt',
    card_uids JSONB DEFAULT '{}',
    auth_mode VARCHAR(50) DEFAULT 'pin_only',
    mqtt_backend VARCHAR(50) DEFAULT 'tuya',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE access_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES input_devices(id) ON DELETE CASCADE,
    access_type VARCHAR(50) NOT NULL,
    card_uid VARCHAR(255),
    pin_hash VARCHAR(255),
    ip_address VARCHAR(45),
    success BOOLEAN,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Índices para performance
CREATE INDEX idx_input_devices_tenant_id ON input_devices(tenant_id);
CREATE INDEX idx_access_logs_tenant_id ON access_logs(tenant_id);
CREATE INDEX idx_access_logs_device_id ON access_logs(device_id);

-- 7. RLS Policies — fail-closed por padrão
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE input_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;

-- Policy: tenants (apenas para superuser, não para app_user)
CREATE POLICY tenants_rls_policy ON tenants
    FOR ALL
    USING (
        current_setting('app.current_tenant_id', true) IS NOT NULL
        AND tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

-- Policy: input_devices (SELECT, INSERT, UPDATE, DELETE isoladas por tenant)
CREATE POLICY input_devices_select_policy ON input_devices
    FOR SELECT
    USING (
        current_setting('app.current_tenant_id', true) IS NOT NULL
        AND tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

CREATE POLICY input_devices_insert_policy ON input_devices
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NOT NULL
        AND tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

CREATE POLICY input_devices_update_policy ON input_devices
    FOR UPDATE
    USING (
        current_setting('app.current_tenant_id', true) IS NOT NULL
        AND tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

CREATE POLICY input_devices_delete_policy ON input_devices
    FOR DELETE
    USING (
        current_setting('app.current_tenant_id', true) IS NOT NULL
        AND tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

-- Policy: access_logs (isoladas por tenant via device_id FK)
CREATE POLICY access_logs_select_policy ON access_logs
    FOR SELECT
    USING (
        current_setting('app.current_tenant_id', true) IS NOT NULL
        AND tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

CREATE POLICY access_logs_insert_policy ON access_logs
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_tenant_id', true) IS NOT NULL
        AND tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

CREATE POLICY access_logs_delete_policy ON access_logs
    FOR DELETE
    USING (
        current_setting('app.current_tenant_id', true) IS NOT NULL
        AND tenant_id::TEXT = current_setting('app.current_tenant_id', true)
    );

-- 8. Permissões para app_user (acesso mínimo com RLS)
GRANT CONNECT ON DATABASE jfa_test TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenants TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON input_devices TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON access_logs TO app_user;

-- Permissões para sequences (para UUID auto-generation)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- 9. Verificar instalação
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
