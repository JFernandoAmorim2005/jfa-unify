"""
Schemas Pydantic para o recurso Tenant.
Alinhado com modelo Tenant (migração 001).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Nome da organização")


class TenantCreate(TenantBase):
    """Dados necessários para criar um tenant."""
    pass


class TenantRead(TenantBase):
    """Representação completa de um tenant (resposta da API)."""
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
