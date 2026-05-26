"""002_enable_rls

Activa Row-Level Security (RLS) nas tabelas multi-tenant do JFA_Unify.

Estratégia:
  - Cada sessão PostgreSQL define a variável de sessão 'app.current_tenant_id'
    antes de qualquer query (ex.: SET LOCAL app.current_tenant_id = '<uuid>').
  - As políticas RLS filtram automaticamente todas as linhas pelo tenant_id.

NOTA SEGURANÇA: Usamos current_setting('app.current_tenant_id', true) com o
segundo argumento `missing_ok = true`. Isto devolve NULL quando a variável não
está definida (ex.: ligações de manutenção sem contexto). O cast ::uuid de NULL
devolve NULL, e tenant_id = NULL é sempre FALSE — a política falha fechada
(zero linhas expostas) em vez de lançar uma excepção. Esta é a forma mais segura.

Revisão: 002
Revisão anterior: 001
"""

from alembic import op

# ---------------------------------------------------------------------------
# Metadados Alembic
# ---------------------------------------------------------------------------
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

# Tabelas que recebem RLS
_RLS_TABLES = ["input_devices", "access_logs", "mqtt_topic_mappings"]

# Nomes das políticas (prefixo consistente para fácil auditoria)
_POLICY_PREFIX = "rls_tenant_isolation"


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Activar RLS em cada tabela
    # ------------------------------------------------------------------
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # FORCE RLS aplica-se também a superusers (importante para auditoria).
        # Se preferir excluir superusers, remover FORCE.
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # ------------------------------------------------------------------
    # 2. Políticas RLS — input_devices
    # current_setting(..., true): missing_ok=true → NULL quando não definido
    # NULL::uuid = NULL → FALSE → sem linhas expostas (fail-closed)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY rls_tenant_isolation_input_devices
        ON input_devices
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    """)

    # ------------------------------------------------------------------
    # 3. Políticas RLS — access_logs
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY rls_tenant_isolation_access_logs
        ON access_logs
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    """)

    # ------------------------------------------------------------------
    # 4. Políticas RLS — mqtt_topic_mappings
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY rls_tenant_isolation_mqtt_topic_mappings
        ON mqtt_topic_mappings
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    """)


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------
def downgrade() -> None:
    # Remover políticas antes de desactivar RLS
    op.execute("DROP POLICY IF EXISTS rls_tenant_isolation_mqtt_topic_mappings ON mqtt_topic_mappings")
    op.execute("DROP POLICY IF EXISTS rls_tenant_isolation_access_logs ON access_logs")
    op.execute("DROP POLICY IF EXISTS rls_tenant_isolation_input_devices ON input_devices")

    for table in reversed(_RLS_TABLES):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
