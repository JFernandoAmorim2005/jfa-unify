"""
Modelo InputDevice — dispositivo de entrada (PIN pad ou leitor de cartão).
Alinhado com migração 001_initial_schema.py.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, BYTEA, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class InputDevice(Base):
    """
    Dispositivo de entrada — leitor de PIN pad, cartão RFID/NFC, ou híbrido.
    Associado a um tenant e a um tópico MQTT físico.

    Segurança:
      - pin_salt: salt por-device (256-bit) para isolamento de hashes.
      - card_uids: JSONB {card_uid -> true} suporta múltiplos cartões por device.
      - auth_mode: 'pin_only' | 'card_only' | 'pin_and_card' (migração usa VARCHAR).
    """

    __tablename__ = "input_devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # Isolamento multi-tenant — RLS filtra por este campo
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Tipo de dispositivo: 'pin_pad' | 'card_reader' | 'hybrid'
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Algoritmo de hash do PIN: 'bcrypt' (padrão) ou 'argon2'
    pin_hash_algorithm: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'bcrypt'")
    )
    # Salt por-device (BYTEA) — rotação independente por dispositivo
    pin_salt: Mapped[bytes] = mapped_column(BYTEA(), nullable=False)
    # {card_uid -> true} para suporte a múltiplos cartões
    card_uids: Mapped[dict] = mapped_column(
        JSONB(astext_type=String()),
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    # Modo de autenticação: 'pin_only' | 'card_only' | 'pin_and_card'
    auth_mode: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'pin_only'")
    )
    # Tópico MQTT físico (obrigatório)
    mqtt_topic: Mapped[str] = mapped_column(String(255), nullable=False)
    # Backend MQTT: 'tuya' (MVP) | 'esp32s3' (Phase 3)
    mqtt_backend: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'tuya'")
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("now()"), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<InputDevice id={self.id} name={self.name!r} auth_mode={self.auth_mode!r}>"
        )
