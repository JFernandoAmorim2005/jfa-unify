"""
Router de controlo de acesso — validação de PIN/cartão com grant via MQTT.

Fluxo (quando suite_integration_enabled=True e suite_token_id presente):
  1. Valida credencial (PIN ou cartão) via AccessControlService.
  2. Se credencial OK → consulta saldo no JFA_Suite via SuiteClient.
  3. Se saldo OK → publica comando MQTT no tópico de resposta do dispositivo.
  4. Consome 1 uso do token no JFA_Suite.
  5. Retorna AccessValidateResponse com granted=True.

Quando suite_integration_enabled=False (default) ou suite_token_id ausente:
  → comportamento original sem alteração (retrocompatível com todos os testes existentes).
"""
import json
import logging
import uuid

from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.db.session import get_db_tenant as get_db
from app.middleware.auth import get_tenant_id
from app.schemas.access_event import AccessValidateRequest, AccessValidateResponse
from app.services.access_control import AccessControlService
from app.services.mqtt_topics import TopicBuilder
from app.services.suite_client import (
    SuiteClient,
    SuiteClientError,
    SuiteTokenInsufficient,
    SuiteTokenNotFound,
    get_suite_client,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Tipos de acesso adicionais (integração Suite)
ACCESS_TYPE_INSUFFICIENT_BALANCE = "insufficient_balance"
ACCESS_TYPE_SUITE_ERROR = "suite_error"


@router.post("/validate", response_model=AccessValidateResponse)
async def validate_access(
    request: Request,
    payload: AccessValidateRequest,
    db=Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    suite_client: SuiteClient = Depends(get_suite_client),
):
    """
    Valida uma tentativa de acesso (PIN ou cartão).

    Grava sempre um registo de auditoria, independentemente do resultado.
    Se a integração com JFA_Suite estiver activa e suite_token_id for fornecido,
    verifica saldo antes de emitir o comando MQTT de grant.
    """
    settings = get_settings()
    source_ip = request.client.host if request.client else None
    service = AccessControlService(db)

    # Passo 1: validar credencial (PIN/cartão)
    result = service.validate(payload, tenant_id, source_ip)

    # Se credencial inválida, retorna imediatamente (sem verificar saldo)
    if not result.granted:
        return result

    # Passo 2 a 4: integração com JFA_Suite (opcional, gated por flag + presença do token)
    if (
        settings.suite_integration_enabled
        and payload.suite_token_id is not None
    ):
        result = await _handle_suite_balance_and_grant(
            request=request,
            result=result,
            payload=payload,
            tenant_id=tenant_id,
            suite_client=suite_client,
        )
        return result

    # Sem integração Suite — emitir comando MQTT directamente se serviço disponível
    if result.granted:
        await _publish_mqtt_grant(request, tenant_id, result.device_id)

    return result


async def _handle_suite_balance_and_grant(
    request: Request,
    result: AccessValidateResponse,
    payload: AccessValidateRequest,
    tenant_id: uuid.UUID,
    suite_client: SuiteClient,
) -> AccessValidateResponse:
    """
    Verifica saldo no JFA_Suite, emite comando MQTT e consome 1 uso.

    Returns:
        AccessValidateResponse actualizado com o resultado final.
    """
    from app.services.access_control import _utcnow

    token_id = payload.suite_token_id
    access_point_id = payload.suite_access_point_id or uuid.UUID(int=0)

    # Passo 2: consultar saldo
    try:
        token_data = await suite_client.get_token_balance(token_id)
    except SuiteTokenNotFound:
        logger.warning(
            "Token JFA_Suite %s não encontrado — tenant=%s device=%s",
            token_id, tenant_id, result.device_id,
        )
        return AccessValidateResponse(
            granted=False,
            access_type=ACCESS_TYPE_SUITE_ERROR,
            device_id=result.device_id,
            detail="Token de saldo não encontrado no JFA_Suite.",
            timestamp=_utcnow(),
        )
    except SuiteClientError as exc:
        logger.error("Erro ao contactar JFA_Suite: %s", exc)
        # Em caso de falha de comunicação, falha fechada (deny)
        return AccessValidateResponse(
            granted=False,
            access_type=ACCESS_TYPE_SUITE_ERROR,
            device_id=result.device_id,
            detail="Erro de comunicação com JFA_Suite.",
            timestamp=_utcnow(),
        )

    # Passo 3: verificar saldo
    if not suite_client.has_balance(token_data):
        logger.info(
            "Saldo insuficiente — token=%s usos_restantes=%s status=%s",
            token_id,
            token_data.get("usos_restantes"),
            token_data.get("status"),
        )
        return AccessValidateResponse(
            granted=False,
            access_type=ACCESS_TYPE_INSUFFICIENT_BALANCE,
            device_id=result.device_id,
            detail=f"Saldo insuficiente (usos_restantes={token_data.get('usos_restantes', 0)}).",
            timestamp=_utcnow(),
        )

    # Passo 4: publicar comando MQTT de grant
    await _publish_mqtt_grant(request, tenant_id, result.device_id)

    # Passo 5: consumir 1 uso no JFA_Suite
    try:
        await suite_client.consume_token(token_id, access_point_id)
        logger.info(
            "Token %s consumido com sucesso — device=%s tenant=%s",
            token_id, result.device_id, tenant_id,
        )
    except SuiteTokenInsufficient:
        # Raro — pode acontecer em concorrência entre dois pedidos
        logger.warning(
            "Corrida de consumo: token %s já esgotado após verificação de saldo",
            token_id,
        )
        return AccessValidateResponse(
            granted=False,
            access_type=ACCESS_TYPE_INSUFFICIENT_BALANCE,
            device_id=result.device_id,
            detail="Token esgotado durante processamento (concorrência).",
            timestamp=_utcnow(),
        )
    except SuiteClientError as exc:
        # Grant já foi emitido via MQTT — registar inconsistência mas não negar
        logger.error(
            "Falha ao consumir token %s após MQTT grant (inconsistência): %s",
            token_id, exc,
        )

    return result


async def _publish_mqtt_grant(
    request: Request,
    tenant_id: uuid.UUID,
    device_id: uuid.UUID,
) -> None:
    """
    Publica comando de grant no tópico MQTT do dispositivo.

    Não levanta excepção se o MQTT service não estiver disponível
    (evita quebrar testes que não inicializam o lifespan).
    """
    mqtt_service = getattr(request.app.state, "mqtt_service", None)
    if mqtt_service is None:
        logger.debug("MQTT service não disponível — grant MQTT omitido (ambiente de teste?)")
        return

    topic = TopicBuilder(tenant_id, device_id).access_response()
    grant_payload = json.dumps({
        "action": "grant",
        "tenant_id": str(tenant_id),
        "device_id": str(device_id),
    }).encode()

    try:
        await mqtt_service.adapter.publish(topic, grant_payload, qos=1)
        logger.info("MQTT grant publicado — tópico=%s", topic)
    except Exception as exc:
        logger.error("Erro ao publicar MQTT grant: %s", exc)
