"""003_add_indices

Adiciona índices de performance para as tabelas multi-tenant do JFA_Unify.

Estratégia de indexação:
  - input_devices: lookup por tenant (listagem) e por mqtt_topic (roteamento MQTT)
  - access_logs: lookup por tenant, por device, e por timestamp (relatórios/retenção)
  - mqtt_topic_mappings: lookup por tenant e por logical_topic (roteamento)

NOTA: Os índices em colunas tenant_id têm utilidade limitada com RLS activo
(as queries já filtram por tenant_id via política), mas são essenciais para:
  a) Queries de manutenção executadas por superuser sem RLS
  b) Planeamento do query optimizer antes de aplicar a política RLS
  c) Suporte a JOINs cross-tenant em queries administrativas

Revisão: 003
Revisão anterior: 002
"""

from alembic import op
from sqlalchemy import text as sa_text

# ---------------------------------------------------------------------------
# Metadados Alembic
# ---------------------------------------------------------------------------
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # ------------------------------------------------------------------
    # input_devices
    # ------------------------------------------------------------------
    # Listagem de devices por tenant (query mais frequente)
    op.create_index(
        "idx_input_devices_tenant",
        "input_devices",
        ["tenant_id"],
    )
    # Roteamento MQTT: lookup pelo tópico físico (hot path de mensagens MQTT)
    op.create_index(
        "idx_input_devices_mqtt_topic",
        "input_devices",
        ["mqtt_topic"],
    )

    # ------------------------------------------------------------------
    # access_logs
    # ------------------------------------------------------------------
    # Relatórios de auditoria por tenant
    op.create_index(
        "idx_access_logs_tenant",
        "access_logs",
        ["tenant_id"],
    )
    # Histórico de acessos por device específico
    op.create_index(
        "idx_access_logs_device",
        "access_logs",
        ["device_id"],
    )
    # Queries temporais: dashboards, retenção (GDPR 90-day purge job)
    # DESC para favorecer queries "últimas N entradas"
    op.create_index(
        "idx_access_logs_timestamp",
        "access_logs",
        [sa_text("timestamp DESC")],
    )

    # ------------------------------------------------------------------
    # mqtt_topic_mappings
    # ------------------------------------------------------------------
    # Lookup de mapeamentos por tenant
    op.create_index(
        "idx_mqtt_mappings_tenant",
        "mqtt_topic_mappings",
        ["tenant_id"],
    )
    # Resolução de tópico lógico → físico (hot path de publicação MQTT)
    op.create_index(
        "idx_mqtt_mappings_logical",
        "mqtt_topic_mappings",
        ["logical_topic"],
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------
def downgrade() -> None:
    op.drop_index("idx_mqtt_mappings_logical", table_name="mqtt_topic_mappings")
    op.drop_index("idx_mqtt_mappings_tenant", table_name="mqtt_topic_mappings")
    op.drop_index("idx_access_logs_timestamp", table_name="access_logs")
    op.drop_index("idx_access_logs_device", table_name="access_logs")
    op.drop_index("idx_access_logs_tenant", table_name="access_logs")
    op.drop_index("idx_input_devices_mqtt_topic", table_name="input_devices")
    op.drop_index("idx_input_devices_tenant", table_name="input_devices")
