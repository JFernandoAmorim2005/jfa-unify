"""
Router de controlo de acesso — validação de PIN e cartão.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db_tenant as get_db
from app.middleware.auth import get_tenant_id
from app.schemas.access_event import AccessValidateRequest, AccessValidateResponse
from app.services.access_control import AccessControlService

router = APIRouter()


@router.post("/validate", response_model=AccessValidateResponse)
def validate_access(
    request: Request,
    payload: AccessValidateRequest,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Valida uma tentativa de acesso (PIN ou cartão).

    Grava sempre um registo de auditoria, independentemente do resultado.
    """
    source_ip = request.client.host if request.client else None
    service = AccessControlService(db)
    return service.validate(payload, tenant_id, source_ip)
