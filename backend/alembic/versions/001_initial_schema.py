"""001_initial_schema

Cria as tabelas base do JFA_Unify:
  - tenants
  - input_devices  (PIN pads, leitores NFC/RFID, híbridos)
  - access_logs    (auditoria de acessos)
  - mqtt_topic_mappings (camada de abstracção multi-backend MQTT)

Revisão: 001
Revisão anterior: None (primeira migração)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Metadados Alembic
# ---------------------------------------------------------------------------
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # Extensões necessárias
    # gen_random_uuid() requer pgcrypto (PostgreSQL < 13).
    # Em PostgreSQL >= 13 gen_random_uuid() está disponível sem pgcrypto,
    # mas instalar é inofensivo e garante compatibilidade com versões mais antigas.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # ------------------------------------------------------------------
    # Tabela: tenants
    # ------------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.VARCHAR(255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # Tabela: input_devices
    # PIN security: nunca guardar PIN em plaintext.
    # pin_salt é por-device (BYTEA) — permite rotação de salt independente.
    # card_uids: JSONB {card_uid -> bool} para suportar múltiplos cartões.
    # auth_mode: 'pin_only' | 'card_only' | 'pin_and_card'
    # mqtt_backend: 'tuya' | 'esp32s3' (abstracção para Phase 3 ESP32-S3)
    # ------------------------------------------------------------------
    op.create_table(
        "input_devices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.VARCHAR(255), nullable=False),
        # 'pin_pad' | 'card_reader' | 'hybrid'
        sa.Column("device_type", sa.VARCHAR(50), nullable=False),
        # Algoritmo de hash do PIN: 'bcrypt' (padrão) ou 'argon2'
        sa.Column(
            "pin_hash_algorithm",
            sa.VARCHAR(50),
            nullable=False,
            server_default=sa.text("'bcrypt'"),
        ),
        # Salt por-device (256-bit recomendado). Rotação independente por device.
        sa.Column("pin_salt", postgresql.BYTEA(), nullable=False),
        # {card_uid -> true} — chave = UID do cartão, valor = registado
        sa.Column(
            "card_uids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Modo de autenticação configurável por device
        sa.Column(
            "auth_mode",
            sa.VARCHAR(50),
            nullable=False,
            server_default=sa.text("'pin_only'"),
        ),
        # Tópico MQTT físico associado ao device
        sa.Column("mqtt_topic", sa.VARCHAR(255), nullable=False),
        # Backend MQTT: 'tuya' (MVP), 'esp32s3' (Phase 3)
        sa.Column(
            "mqtt_backend",
            sa.VARCHAR(50),
            nullable=False,
            server_default=sa.text("'tuya'"),
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Garantia de unicidade: um tópico MQTT por tenant
        sa.UniqueConstraint("tenant_id", "mqtt_topic", name="uq_input_devices_tenant_topic"),
    )

    # ------------------------------------------------------------------
    # Tabela: access_logs (auditoria)
    # pin_hash: nunca guardar o PIN em plaintext — apenas o hash do PIN.
    # ip_address: INET suporta IPv4 e IPv6.
    # access_type: 'pin_valid' | 'pin_invalid' | 'card_read' |
    #              'double_auth_success' | 'double_auth_fail' | etc.
    # ------------------------------------------------------------------
    op.create_table(
        "access_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("input_devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Tipo de evento de acesso
        sa.Column("access_type", sa.VARCHAR(50), nullable=False),
        # UID do cartão apresentado (nullable — nem sempre se usa cartão)
        sa.Column("card_uid", sa.VARCHAR(255), nullable=True),
        # Hash do PIN usado (NUNCA plaintext). Nullable — pode ser acesso só por cartão.
        sa.Column("pin_hash", sa.VARCHAR(255), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        # Endereço IP do pedido (IPv4 ou IPv6)
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # Tabela: mqtt_topic_mappings (camada de abstracção MQTT multi-backend)
    # Mapeia tópicos lógicos (agnósticos) para tópicos físicos por backend.
    # Ex.: 'access/validate' -> 'tuya/hub123/access/validate' (Tuya MVP)
    #                        -> 'esp32/device456/validate'    (Phase 3 ESP32-S3)
    # ------------------------------------------------------------------
    op.create_table(
        "mqtt_topic_mappings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Tópico lógico agnóstico ao hardware: 'access/validate', 'device/status', etc.
        sa.Column("logical_topic", sa.VARCHAR(255), nullable=False),
        # Tópico físico real no broker: 'tuya/hub123/access/validate', etc.
        sa.Column("physical_topic", sa.VARCHAR(255), nullable=False),
        # Backend alvo: 'tuya' | 'esp32s3'
        sa.Column("backend", sa.VARCHAR(50), nullable=False),
        # Um mapeamento único por (tenant, tópico lógico, backend)
        sa.UniqueConstraint(
            "tenant_id", "logical_topic", "backend",
            name="uq_mqtt_mappings_tenant_logical_backend",
        ),
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------
def downgrade() -> None:
    # Remover tabelas em ordem inversa (respeitar dependências FK)
    op.drop_table("mqtt_topic_mappings")
    op.drop_table("access_logs")
    op.drop_table("input_devices")
    op.drop_table("tenants")
    # Não remover as extensões — podem ser usadas por outras aplicações
