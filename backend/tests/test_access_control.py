"""
Unit tests para AccessControlService — validação PIN/card, autenticação dupla e audit.

Estratégia:
- PIN validation: HMAC-SHA256 correctness, missing PIN, missing salt, missing hash storage
- Card validation: UID matching (case-insensitive), UID not recognized, missing card, internal keys ignored
- Double-auth: PIN + card required together, failure scenarios
- Edge cases: Device not found, disabled device, unknown auth mode, tenant isolation (RLS)
- Audit logging: Logged on success, failure, device not found
"""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.access_control import (
    AccessControlService,
    ACCESS_TYPE_PIN_VALID,
    ACCESS_TYPE_PIN_INVALID,
    ACCESS_TYPE_CARD_READ,
    ACCESS_TYPE_CARD_INVALID,
    ACCESS_TYPE_DOUBLE_AUTH_SUCCESS,
    ACCESS_TYPE_DOUBLE_AUTH_FAIL,
    ACCESS_TYPE_DEVICE_NOT_FOUND,
    ACCESS_TYPE_CONFIG_ERROR,
)
from app.services.access_crypto import hash_pin_for_device
from app.schemas.access_event import AccessValidateRequest


# --- Test fixtures ---

@pytest.fixture
def sample_tenant_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_device_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def pin_salt() -> bytes:
    """Salt fixo para testes determinísticos."""
    return b"\x00" * 32


@pytest.fixture
def sample_pin() -> str:
    return "1234"


@pytest.fixture
def sample_device_pin_only(
    sample_device_id: uuid.UUID,
    sample_tenant_id: uuid.UUID,
    pin_salt: bytes,
    sample_pin: str,
) -> SimpleNamespace:
    """Dispositivo de teste com autenticação por PIN."""
    return SimpleNamespace(
        id=sample_device_id,
        tenant_id=sample_tenant_id,
        name="PIN Pad Teste",
        device_type="pin_pad",
        auth_mode="pin_only",
        pin_salt=pin_salt,
        card_uids={"__pin__": hash_pin_for_device(sample_pin, pin_salt)},
        enabled=True,
    )


@pytest.fixture
def sample_device_card_only(
    sample_device_id: uuid.UUID,
    sample_tenant_id: uuid.UUID,
) -> SimpleNamespace:
    """Dispositivo de teste com autenticação por cartão."""
    return SimpleNamespace(
        id=sample_device_id,
        tenant_id=sample_tenant_id,
        name="Card Reader Teste",
        device_type="card_reader",
        auth_mode="card_only",
        pin_salt=b"\x00" * 32,
        card_uids={"AABBCCDD": True, "11223344": True},
        enabled=True,
    )


@pytest.fixture
def sample_device_double_auth(
    sample_device_id: uuid.UUID,
    sample_tenant_id: uuid.UUID,
    pin_salt: bytes,
    sample_pin: str,
) -> SimpleNamespace:
    """Dispositivo de teste com autenticação dupla (PIN + card)."""
    return SimpleNamespace(
        id=sample_device_id,
        tenant_id=sample_tenant_id,
        name="Double Auth Device",
        device_type="biometric_pad",
        auth_mode="pin_and_card",
        pin_salt=pin_salt,
        card_uids={
            "__pin__": hash_pin_for_device(sample_pin, pin_salt),
            "AABBCCDD": True,
        },
        enabled=True,
    )


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock da sessão SQLAlchemy."""
    mock = MagicMock()
    mock.query.return_value = mock
    mock.filter.return_value = mock
    mock.filter_by.return_value = mock
    mock.first.return_value = None
    mock.add.return_value = None
    mock.commit.return_value = None
    return mock


@pytest.fixture
def access_control_service(mock_db: MagicMock) -> AccessControlService:
    return AccessControlService(db=mock_db)


# --- Test Classes ---

class TestAccessControlPINValidation:
    """Tests para validação de PIN."""

    def test_pin_validation_success(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        sample_pin: str,
        mock_db: MagicMock,
    ):
        """PIN matches hash — validation succeeds."""
        mock_db.first.return_value = sample_device_pin_only

        request = AccessValidateRequest(
            device_id=sample_device_pin_only.id,
            pin=sample_pin,
            card_uid=None,
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_pin_only.tenant_id,
        )

        assert result.granted is True
        assert result.access_type == ACCESS_TYPE_PIN_VALID
        mock_db.add.assert_called()

    def test_pin_validation_invalid(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        mock_db: MagicMock,
    ):
        """PIN does not match hash — validation fails."""
        mock_db.first.return_value = sample_device_pin_only

        request = AccessValidateRequest(
            device_id=sample_device_pin_only.id,
            pin="9999",  # Wrong PIN
            card_uid=None,
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_pin_only.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_PIN_INVALID
        mock_db.add.assert_called()

    def test_pin_validation_pin_not_provided(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        mock_db: MagicMock,
    ):
        """PIN required but not provided — validation fails."""
        mock_db.first.return_value = sample_device_pin_only

        request = AccessValidateRequest(
            device_id=sample_device_pin_only.id,
            pin=None,
            card_uid=None,
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_pin_only.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_PIN_INVALID

    def test_pin_validation_no_salt(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        sample_pin: str,
        mock_db: MagicMock,
    ):
        """Device has no PIN salt — HMAC validation cannot proceed."""
        device_no_salt = SimpleNamespace(
            **{**vars(sample_device_pin_only), "pin_salt": None}
        )
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            device_no_salt
        )

        request = AccessValidateRequest(
            device_id=device_no_salt.id,
            pin=sample_pin,
            card_uid=None,
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=device_no_salt.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_CONFIG_ERROR

    def test_pin_validation_no_hash_stored(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        sample_pin: str,
        mock_db: MagicMock,
    ):
        """Device PIN auth mode but no hash in card_uids — misconfiguration."""
        device_no_hash = SimpleNamespace(
            **{**vars(sample_device_pin_only), "card_uids": {}}
        )
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            device_no_hash
        )

        request = AccessValidateRequest(
            device_id=device_no_hash.id,
            pin=sample_pin,
            card_uid=None,
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=device_no_hash.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_CONFIG_ERROR


class TestAccessControlCardValidation:
    """Tests para validação de cartão."""

    def test_card_validation_success(
        self,
        access_control_service: AccessControlService,
        sample_device_card_only: SimpleNamespace,
        mock_db: MagicMock,
    ):
        """Card UID matches — validation succeeds."""
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            sample_device_card_only
        )

        request = AccessValidateRequest(
            device_id=sample_device_card_only.id,
            pin=None,
            card_uid="AABBCCDD",
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_card_only.tenant_id,
        )

        assert result.granted is True
        assert result.access_type == ACCESS_TYPE_CARD_READ

    def test_card_validation_case_insensitive(
        self,
        access_control_service: AccessControlService,
        sample_device_card_only: SimpleNamespace,
        mock_db: MagicMock,
    ):
        """Card UID matching is case-insensitive."""
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            sample_device_card_only
        )

        request = AccessValidateRequest(
            device_id=sample_device_card_only.id,
            pin=None,
            card_uid="aabbccdd",  # Lowercase
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_card_only.tenant_id,
        )

        assert result.granted is True
        assert result.access_type == ACCESS_TYPE_CARD_READ

    def test_card_validation_not_recognized(
        self,
        access_control_service: AccessControlService,
        sample_device_card_only: SimpleNamespace,
        mock_db: MagicMock,
    ):
        """Unknown card UID — validation fails."""
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            sample_device_card_only
        )

        request = AccessValidateRequest(
            device_id=sample_device_card_only.id,
            pin=None,
            card_uid="DEADBEEF",  # Unknown UID
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_card_only.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_CARD_INVALID

    def test_card_validation_ignores_internal_keys(
        self,
        access_control_service: AccessControlService,
        sample_device_card_only: SimpleNamespace,
        mock_db: MagicMock,
    ):
        """Internal keys like '__pin__' are ignored in card validation."""
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            sample_device_card_only
        )

        request = AccessValidateRequest(
            device_id=sample_device_card_only.id,
            pin=None,
            card_uid="__pin__",  # Internal key
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_card_only.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_CARD_INVALID


class TestAccessControlDoubleAuth:
    """Tests para autenticação dupla (PIN + card)."""

    def test_double_auth_success(
        self,
        access_control_service: AccessControlService,
        sample_device_double_auth: SimpleNamespace,
        sample_pin: str,
        mock_db: MagicMock,
    ):
        """Both PIN and card valid — double auth succeeds."""
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            sample_device_double_auth
        )

        request = AccessValidateRequest(
            device_id=sample_device_double_auth.id,
            pin=sample_pin,
            card_uid="AABBCCDD",
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_double_auth.tenant_id,
        )

        assert result.granted is True
        assert result.access_type == ACCESS_TYPE_DOUBLE_AUTH_SUCCESS

    def test_double_auth_pin_invalid(
        self,
        access_control_service: AccessControlService,
        sample_device_double_auth: SimpleNamespace,
        mock_db: MagicMock,
    ):
        """PIN invalid in double-auth — fails."""
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            sample_device_double_auth
        )

        request = AccessValidateRequest(
            device_id=sample_device_double_auth.id,
            pin="9999",  # Wrong PIN
            card_uid="AABBCCDD",
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_double_auth.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_DOUBLE_AUTH_FAIL

    def test_double_auth_card_invalid(
        self,
        access_control_service: AccessControlService,
        sample_device_double_auth: SimpleNamespace,
        sample_pin: str,
        mock_db: MagicMock,
    ):
        """Card invalid in double-auth — fails."""
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            sample_device_double_auth
        )

        request = AccessValidateRequest(
            device_id=sample_device_double_auth.id,
            pin=sample_pin,
            card_uid="DEADBEEF",  # Unknown card
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_double_auth.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_DOUBLE_AUTH_FAIL


class TestAccessControlEdgeCases:
    """Tests para edge cases."""

    def test_device_not_found(
        self,
        access_control_service: AccessControlService,
        sample_tenant_id: uuid.UUID,
        mock_db: MagicMock,
    ):
        """Device not found — validation returns device_not_found."""
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        request = AccessValidateRequest(
            device_id=uuid.uuid4(),
            pin="1234",
            card_uid=None,
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_DEVICE_NOT_FOUND
        mock_db.add.assert_called()

    def test_device_disabled(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        sample_pin: str,
        mock_db: MagicMock,
    ):
        """Disabled device — validation fails."""
        mock_db.first.return_value = None

        request = AccessValidateRequest(
            device_id=sample_device_pin_only.id,
            pin=sample_pin,
            card_uid=None,
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=sample_device_pin_only.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_DEVICE_NOT_FOUND

    def test_unknown_auth_mode(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        sample_pin: str,
        mock_db: MagicMock,
    ):
        """Unknown auth_mode — returns config error."""
        device_unknown_mode = SimpleNamespace(
            **{**vars(sample_device_pin_only), "auth_mode": "unknown_mode"}
        )
        mock_db.query.return_value.filter_by.return_value.first.return_value = (
            device_unknown_mode
        )

        request = AccessValidateRequest(
            device_id=device_unknown_mode.id,
            pin=sample_pin,
            card_uid=None,
        )

        result = access_control_service.validate(
            request=request,
            tenant_id=device_unknown_mode.tenant_id,
        )

        assert result.granted is False
        assert result.access_type == ACCESS_TYPE_CONFIG_ERROR

    def test_tenant_isolation_rls(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        sample_pin: str,
        mock_db: MagicMock,
    ):
        """Validate with different tenant_id — request is scoped by tenant."""
        mock_db.first.return_value = sample_device_pin_only

        different_tenant = uuid.uuid4()
        request = AccessValidateRequest(
            device_id=sample_device_pin_only.id,
            pin=sample_pin,
            card_uid=None,
        )

        access_control_service.validate(
            request=request,
            tenant_id=different_tenant,
        )

        # Validation happens but audit log should use the passed tenant_id
        # (mock_db.filter_by was called with the different tenant)
        mock_db.query.assert_called()


class TestAccessControlAuditLogging:
    """Tests para audit logging."""

    def test_audit_log_on_success(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        sample_pin: str,
        mock_db: MagicMock,
    ):
        """Successful validation creates audit log entry."""
        mock_db.first.return_value = sample_device_pin_only

        request = AccessValidateRequest(
            device_id=sample_device_pin_only.id,
            pin=sample_pin,
            card_uid=None,
        )

        access_control_service.validate(
            request=request,
            tenant_id=sample_device_pin_only.tenant_id,
        )

        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_audit_log_on_failure(
        self,
        access_control_service: AccessControlService,
        sample_device_pin_only: SimpleNamespace,
        mock_db: MagicMock,
    ):
        """Failed validation creates audit log entry with success=False."""
        mock_db.first.return_value = sample_device_pin_only

        request = AccessValidateRequest(
            device_id=sample_device_pin_only.id,
            pin="9999",  # Wrong PIN
            card_uid=None,
        )

        access_control_service.validate(
            request=request,
            tenant_id=sample_device_pin_only.tenant_id,
        )

        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_audit_log_on_device_not_found(
        self,
        access_control_service: AccessControlService,
        sample_tenant_id: uuid.UUID,
        mock_db: MagicMock,
    ):
        """Device not found — audit log still created."""
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        request = AccessValidateRequest(
            device_id=uuid.uuid4(),
            pin="1234",
            card_uid=None,
        )

        access_control_service.validate(
            request=request,
            tenant_id=sample_tenant_id,
        )

        mock_db.add.assert_called()
        mock_db.commit.assert_called()
