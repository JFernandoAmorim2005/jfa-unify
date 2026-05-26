"""
Serviço de controlo de acesso — lógica de validação de PIN e cartão.
Alinhado com modelos da migração 001 (access_logs.access_type, success, etc.).
"""
import hmac
import logging
import uuid
from datetime import datetime, timezone

def _utcnow() -> datetime:
    """Retorna hora UTC actual (compatível com Python 3.12+)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy.orm import Session

from app.models.device import InputDevice
from app.models.access_log import AccessLog
from app.schemas.access_event import AccessValidateRequest, AccessValidateResponse
from app.services.access_crypto import _compute_pin_hash

logger = logging.getLogger(__name__)

# Tipos de evento de acesso (alinhados com migração 001)
ACCESS_TYPE_PIN_VALID = "pin_valid"
ACCESS_TYPE_PIN_INVALID = "pin_invalid"
ACCESS_TYPE_CARD_READ = "card_read"
ACCESS_TYPE_CARD_INVALID = "card_invalid"
ACCESS_TYPE_DOUBLE_AUTH_SUCCESS = "double_auth_success"
ACCESS_TYPE_DOUBLE_AUTH_FAIL = "double_auth_fail"
ACCESS_TYPE_DEVICE_NOT_FOUND = "device_not_found"
ACCESS_TYPE_CONFIG_ERROR = "config_error"


class AccessControlService:
    """
    Lógica de negócio para validação de tentativas de acesso.
    Grava sempre um registo de auditoria, independentemente do resultado.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def validate(
        self,
        request: AccessValidateRequest,
        tenant_id: uuid.UUID,
        source_ip: str | None = None,
    ) -> AccessValidateResponse:
        """
        Valida uma tentativa de acesso (PIN ou cartão).

        Fluxo:
        1. Carrega dispositivo (verifica tenant e estado enabled).
        2. Verifica modo de autenticação e credenciais.
        3. Grava registo de auditoria.
        4. Retorna resposta com resultado.
        """
        device = self._load_device(request.device_id, tenant_id)

        if device is None:
            self._log_event(
                tenant_id=tenant_id,
                device_id=request.device_id,
                access_type=ACCESS_TYPE_DEVICE_NOT_FOUND,
                card_uid=request.card_uid,
                pin_hash=None,
                success=False,
                ip_address=source_ip,
            )
            return AccessValidateResponse(
                granted=False,
                access_type=ACCESS_TYPE_DEVICE_NOT_FOUND,
                device_id=request.device_id,
                detail="Dispositivo não encontrado ou inactivo.",
                timestamp=_utcnow(),
            )

        granted, access_type, pin_hash_used, detail = self._check_credentials(
            request, device
        )

        self._log_event(
            tenant_id=tenant_id,
            device_id=device.id,
            access_type=access_type,
            card_uid=request.card_uid,
            pin_hash=pin_hash_used,
            success=granted,
            ip_address=source_ip,
        )

        return AccessValidateResponse(
            granted=granted,
            access_type=access_type,
            device_id=device.id,
            detail=detail,
            timestamp=_utcnow(),
        )

    # --- Métodos auxiliares ---

    def _load_device(
        self, device_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> InputDevice | None:
        """Carrega dispositivo verificando pertença ao tenant e estado enabled."""
        return (
            self.db.query(InputDevice)
            .filter(
                InputDevice.id == device_id,
                InputDevice.tenant_id == tenant_id,
                InputDevice.enabled.is_(True),
            )
            .first()
        )

    def _check_credentials(
        self, request: AccessValidateRequest, device: InputDevice
    ) -> tuple[bool, str, str | None, str]:
        """
        Verifica credenciais conforme o modo de autenticação do dispositivo.

        Returns:
            Tuplo (granted, access_type, pin_hash_used, detail).
        """
        mode = device.auth_mode

        if mode == "pin_only":
            return self._check_pin(request, device)

        if mode == "card_only":
            granted, access_type, detail = self._check_card(request, device)
            return granted, access_type, None, detail

        if mode == "pin_and_card":
            pin_ok, _, pin_hash_used, _ = self._check_pin(request, device)
            card_ok, _, _, _ = self._check_card(request, device), None, None, None
            # Simplificação: verificar cartão separadamente
            card_granted, card_type, card_detail = self._check_card(request, device)
            if pin_ok and card_granted:
                return True, ACCESS_TYPE_DOUBLE_AUTH_SUCCESS, pin_hash_used, "PIN e cartão verificados."
            return False, ACCESS_TYPE_DOUBLE_AUTH_FAIL, pin_hash_used, "Requer PIN e cartão válidos."

        return False, ACCESS_TYPE_CONFIG_ERROR, None, f"Modo desconhecido: {mode}"

    def _check_pin(
        self, request: AccessValidateRequest, device: InputDevice
    ) -> tuple[bool, str, str | None, str]:
        """Verifica PIN. Retorna (granted, access_type, pin_hash, detail)."""
        if not request.pin:
            return False, ACCESS_TYPE_PIN_INVALID, None, "PIN não fornecido."
        if not device.pin_salt:
            return False, ACCESS_TYPE_CONFIG_ERROR, None, "PIN não configurado."

        computed_hash = _compute_pin_hash(request.pin, device.pin_salt)
        # Nota: o hash armazenado está no campo card_uids ou numa tabela separada.
        # Para MVP: comparar com hash armazenado em memória (ver DeviceCreate).
        # Em produção: hash verificado via bcrypt/argon2 com pin_salt.
        # Aqui verificamos o hash derivado do PIN usando HMAC com o salt do device.
        success = hmac.compare_digest(
            computed_hash,
            _compute_pin_hash(request.pin, device.pin_salt),
        )
        # O hash computado é sempre igual ao do próprio PIN — precisamos armazenar
        # o hash esperado. Para MVP usamos a SECRET_KEY + pin_salt como verificação.
        # O hash "armazenado" é gerado na criação e guardado em card_uids["__pin__"].
        stored_pin_hash = device.card_uids.get("__pin__") if device.card_uids else None
        if not stored_pin_hash:
            return False, ACCESS_TYPE_CONFIG_ERROR, None, "Hash do PIN não configurado."

        verified = hmac.compare_digest(computed_hash, stored_pin_hash)
        if verified:
            return True, ACCESS_TYPE_PIN_VALID, computed_hash, "PIN válido."
        return False, ACCESS_TYPE_PIN_INVALID, computed_hash, "PIN inválido."

    def _check_card(
        self, request: AccessValidateRequest, device: InputDevice
    ) -> tuple[bool, str, str]:
        """Verifica UID do cartão. Retorna (granted, access_type, detail)."""
        if not request.card_uid:
            return False, ACCESS_TYPE_CARD_INVALID, "UID do cartão não fornecido."
        card_uids: dict = device.card_uids or {}
        # Comparação case-insensitive — tolerância a leitores diferentes
        uid_upper = request.card_uid.upper()
        if uid_upper in {k.upper() for k in card_uids if not k.startswith("__")}:
            return True, ACCESS_TYPE_CARD_READ, "Cartão válido."
        return False, ACCESS_TYPE_CARD_INVALID, "Cartão não reconhecido."

    def _log_event(
        self,
        tenant_id: uuid.UUID,
        device_id: uuid.UUID,
        access_type: str,
        card_uid: str | None,
        pin_hash: str | None,
        success: bool,
        ip_address: str | None,
    ) -> None:
        """Insere registo de auditoria (append-only)."""
        entry = AccessLog(
            tenant_id=tenant_id,
            device_id=device_id,
            access_type=access_type,
            card_uid=card_uid,
            pin_hash=pin_hash,
            success=success,
            ip_address=ip_address,
        )
        self.db.add(entry)
        self.db.commit()
        logger.info(
            "Acesso %s (success=%s) — device_id=%s tenant_id=%s",
            access_type, success, device_id, tenant_id,
        )
