"""
Modelo Tenant — representa uma organização cliente no sistema multi-tenant.
Alinhado com migração 001_initial_schema.py.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Tenant(Base):
    """
    Tenant (organização) — unidade base de isolamento de dados.
    RLS activa nas tabelas dependentes (ver migração 002_enable_rls.py).
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("now()"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name!r}>"
