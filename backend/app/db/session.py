"""
Dependency injection da sessão de base de dados para FastAPI.

RLS multi-tenant: get_db_for_tenant() activa SET LOCAL app.current_tenant_id
por sessão, necessário para que as políticas RLS filtrem correctamente.
"""
import uuid
from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, set_tenant_context
from app.middleware.auth import get_tenant_id


def get_db() -> Generator[Session, None, None]:
    """
    Dependency FastAPI básica — sessão sem contexto de tenant.
    Usar apenas em rotas públicas ou administrativas (sem RLS).

    Para rotas autenticadas, usar get_db_tenant() que activa RLS.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_tenant(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> Generator[Session, None, None]:
    """
    Dependency FastAPI com contexto de tenant para RLS.

    Abre sessão, executa SET LOCAL app.current_tenant_id = <uuid>,
    e garante fecho após o pedido.

    As políticas RLS em input_devices, access_logs e mqtt_topic_mappings
    usam current_setting('app.current_tenant_id', true) para filtrar.

    Uso:
        @router.get("/dispositivos")
        def list_devices(db: Session = Depends(get_db_tenant)):
            # Todas as queries nesta db já estão filtradas por tenant_id via RLS
            ...
    """
    db = SessionLocal()
    try:
        set_tenant_context(db, str(tenant_id))
        yield db
    finally:
        db.close()
