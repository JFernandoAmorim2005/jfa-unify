"""
Schemas Pydantic para InputDevice (PIN pad / leitor de cartão).
Alinhado com modelo InputDevice (migração 001).

Campos de segurança:
  - pin_plain: recebido na criação, nunca persistido em claro.
  - pin_salt e pin_hash_algorithm são geridos pelo serviço.
  - card_uids: lista de UIDs autorizados (internamente como JSONB {uid -> true}).
"""
import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class DeviceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., description="'pin_pad' | 'card_reader' | 'hybrid'")
    mqtt_topic: str = Field(..., max_length=255,
                             description="Tópico MQTT físico do dispositivo")
    mqtt_backend: str = Field("tuya", description="'tuya' | 'esp32s3'")
    auth_mode: str = Field("pin_only",
                            description="'pin_only' | 'card_only' | 'pin_and_card'")
    enabled: bool = True


class DeviceCreate(DeviceBase):
    """
    Dados para criação de dispositivo.
    PIN e card_uids opcionais; hash e salt gerados no serviço.
    """
    tenant_id: uuid.UUID
    # PIN em texto limpo — o serviço gera salt e hash; nunca persistido em claro
    pin_plain: str | None = Field(
        None, min_length=4, max_length=12,
        description="PIN em texto limpo (4-12 dígitos); será convertido em hash"
    )
    # Lista de UIDs de cartão autorizados (hex strings)
    card_uids: List[str] = Field(
        default_factory=list,
        description="Lista de UIDs de cartão RFID/NFC autorizados"
    )


class DeviceUpdate(BaseModel):
    """Campos actualizáveis de um dispositivo."""
    name: str | None = Field(None, min_length=1, max_length=255)
    auth_mode: str | None = None
    pin_plain: str | None = Field(None, min_length=4, max_length=12)
    card_uids: List[str] | None = None
    enabled: bool | None = None


class DeviceRead(DeviceBase):
    """Representação pública de um dispositivo (sem pin_salt nem hashes)."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    # Número de cartões registados (sem expor os UIDs directamente)
    card_count: int = Field(0, description="Número de cartões registados")
    created_at: datetime

    model_config = {"from_attributes": True}
