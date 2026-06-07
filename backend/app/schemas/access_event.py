"""
Schemas Pydantic para eventos de controlo de acesso e auditoria.
Alinhado com modelo AccessLog (migração 001).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AccessValidateRequest(BaseModel):
    """Pedido de validação de acesso via API."""
    device_id: uuid.UUID = Field(..., description="ID do dispositivo de entrada")
    # Exactamente um de pin ou card_uid deve estar presente (validação no serviço)
    pin: str | None = Field(
        None, min_length=4, max_length=12,
        description="PIN em texto limpo para verificação"
    )
    card_uid: str | None = Field(
        None, max_length=255,
        description="UID do cartão RFID/NFC para verificação"
    )
    # Integração opcional com JFA_Suite — token pré-pago para verificação de saldo.
    # Apenas relevante quando SUITE_INTEGRATION_ENABLED=true.
    suite_token_id: uuid.UUID | None = Field(
        None,
        description="UUID do token pré-pago em JFA_Suite (opcional — verificação de saldo)",
    )
    # UUID do access_point em JFA_Suite (necessário se suite_token_id presente).
    suite_access_point_id: uuid.UUID | None = Field(
        None,
        description="UUID do access_point em JFA_Suite (usado com suite_token_id)",
    )


class AccessValidateResponse(BaseModel):
    """Resposta à validação de acesso."""
    granted: bool
    access_type: str = Field(..., description="Tipo de evento registado")
    device_id: uuid.UUID
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AccessLogRead(BaseModel):
    """Registo de auditoria (leitura)."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    device_id: uuid.UUID
    access_type: str
    card_uid: str | None
    pin_hash: str | None = Field(None, description="Hash do PIN (nunca plaintext)")
    success: bool
    ip_address: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}
