"""
Modelo AccessLog — registo de auditoria de tentativas de acesso.
Alinhado com migração 001_initial_schema.py.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AccessLog(Base):
    """
    Registo imutável de cada evento de acesso.
    Nunca actualizar — apenas inserir (append-only audit trail).

    Segurança:
      - pin_hash: hash do PIN usado, nunca texto limpo.
      - ip_address: INET suporta IPv4 e IPv6.
    """

    __tablename__ = "access_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # Isolamento multi-tenant
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("input_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Tipo de evento: 'pin_valid' | 'pin_invalid' | 'card_read' |
    # 'double_auth_success' | 'double_auth_fail' | etc.
    access_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # UID do cartão apresentado (nullable — nem sempre se usa cartão)
    card_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Hash do PIN usado (NUNCA plaintext). Nullable — acesso só por cartão.
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    # Endereço IP do pedido (IPv4 ou IPv6)
    ip_address: Mapped[str | None] = mapped_column(INET(), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("now()"), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<AccessLog id={self.id} access_type={self.access_type!r} "
            f"success={self.success} timestamp={self.timestamp}>"
        )
