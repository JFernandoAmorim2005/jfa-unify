"""
Router de auditoria — consulta de registos de acesso.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_tenant as get_db
from app.middleware.auth import get_tenant_id
from app.models.access_log import AccessLog
from app.schemas.access_event import AccessLogRead

router = APIRouter()


@router.get("/", response_model=List[AccessLogRead])
def list_logs(
    device_id: uuid.UUID | None = Query(None, description="Filtrar por dispositivo"),
    limit: int = Query(50, ge=1, le=500, description="Número máximo de registos"),
    offset: int = Query(0, ge=0, description="Deslocamento para paginação"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Lista registos de auditoria do tenant, do mais recente para o mais antigo.
    Suporta filtragem por dispositivo e paginação.
    """
    query = db.query(AccessLog).filter(AccessLog.tenant_id == tenant_id)

    if device_id:
        query = query.filter(AccessLog.device_id == device_id)

    return (
        query.order_by(AccessLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
