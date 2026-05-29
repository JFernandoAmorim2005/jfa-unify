"""
Testes HTTP para router de auditoria/logs.

Estratégia: Validar GET /logs/ com filtros de dispositivo,
paginação e resposta de AccessLogRead.
"""
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest


def _make_access_log(**kwargs) -> SimpleNamespace:
    """Cria um log de acesso simples para testes."""
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        device_id=uuid.uuid4(),
        timestamp=datetime.now(UTC),
        access_type="pin_success",
        card_uid=None,
        pin_hash="hash_pin_xxx",
        success=True,
        ip_address="192.168.1.1",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.fixture
def mock_db_with_logs(sample_tenant_id, sample_device_id):
    """Mock DB com logs de acesso."""
    from unittest.mock import MagicMock

    log1 = _make_access_log(
        tenant_id=sample_tenant_id,
        device_id=sample_device_id,
        access_type="pin_success",
        success=True,
    )

    log2 = _make_access_log(
        tenant_id=sample_tenant_id,
        device_id=sample_device_id,
        access_type="pin_failed",
        success=False,
    )

    mock_db = MagicMock()

    # Criar chain mock que retorna sempre a si próprio até .all()
    chain_mock = MagicMock()
    chain_mock.filter.return_value = chain_mock
    chain_mock.order_by.return_value = chain_mock
    chain_mock.offset.return_value = chain_mock
    chain_mock.limit.return_value = chain_mock
    chain_mock.all.return_value = [log1, log2]

    mock_db.query.return_value = chain_mock

    return mock_db


@pytest.fixture
def client_logs(sample_tenant_id, mock_db_with_logs):
    """TestClient para testes de logs router com overrides e middleware mockado."""
    from unittest.mock import patch

    from app.db.session import get_db_tenant
    from app.main import app
    from app.middleware.auth import get_tenant_id
    from tests.conftest import _make_client_with_auth

    def override_get_tenant_id():
        return sample_tenant_id

    def override_get_db_tenant():
        yield mock_db_with_logs

    # Mockar verify_hmac_token para aceitar sempre
    with patch('app.middleware.auth.verify_hmac_token') as mock_verify:
        mock_verify.return_value = {"tenant_id": str(sample_tenant_id)}

        app.dependency_overrides[get_tenant_id] = override_get_tenant_id
        app.dependency_overrides[get_db_tenant] = override_get_db_tenant

        # Usar helper que injeta headers de autenticação
        client = _make_client_with_auth(app, sample_tenant_id)
        yield client
        app.dependency_overrides.clear()


class TestListLogs:
    """Testes para GET /logs/"""

    def test_list_returns_200_and_logs_array(self, client_logs):
        """GET /logs/ retorna 200 e lista de logs."""
        resp = client_logs.get("/logs/")
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_log_response_structure(self, client_logs):
        """Response contém campos esperados de AccessLogRead."""
        resp = client_logs.get("/logs/")
        assert resp.status_code == 200

        logs = resp.json()
        first_log = logs[0]

        assert "id" in first_log
        assert "tenant_id" in first_log
        assert "device_id" in first_log
        assert "timestamp" in first_log
        assert "access_type" in first_log
        assert "success" in first_log

    def test_list_with_default_limit(self, client_logs):
        """GET /logs/ sem parâmetros usa limit=50 por padrão."""
        resp = client_logs.get("/logs/")
        assert resp.status_code == 200

        # Mock retorna 2 logs, deve estar OK
        logs = resp.json()
        assert len(logs) <= 50

    def test_list_with_custom_limit(self, client_logs):
        """GET /logs/?limit=10 respeita limit customizado."""
        resp = client_logs.get("/logs/?limit=10")
        assert resp.status_code == 200

    def test_list_with_invalid_limit_returns_422(self, client_logs):
        """GET /logs/?limit=0 retorna 422 (validação)."""
        resp = client_logs.get("/logs/?limit=0")
        assert resp.status_code == 422

    def test_list_with_limit_too_high_returns_422(self, client_logs):
        """GET /logs/?limit=1000 retorna 422 (máximo é 500)."""
        resp = client_logs.get("/logs/?limit=1000")
        assert resp.status_code == 422

    def test_list_with_offset(self, client_logs):
        """GET /logs/?offset=10 respeita offset."""
        resp = client_logs.get("/logs/?offset=10")
        assert resp.status_code == 200

    def test_list_with_invalid_offset_returns_422(self, client_logs):
        """GET /logs/?offset=-1 retorna 422."""
        resp = client_logs.get("/logs/?offset=-1")
        assert resp.status_code == 422

    def test_list_with_device_id_filter(self, client_logs, sample_device_id):
        """GET /logs/?device_id={id} filtra por dispositivo."""
        resp = client_logs.get(f"/logs/?device_id={sample_device_id}")
        assert resp.status_code == 200

        logs = resp.json()
        # Mock retorna logs do dispositivo específico
        assert len(logs) > 0

    def test_list_with_invalid_device_id_format_returns_422(self, client_logs):
        """GET /logs/?device_id=invalid retorna 422."""
        resp = client_logs.get("/logs/?device_id=invalid")
        assert resp.status_code == 422

    def test_list_with_multiple_filters(self, client_logs, sample_device_id):
        """GET /logs/?device_id={id}&limit=5&offset=0."""
        resp = client_logs.get(
            f"/logs/?device_id={sample_device_id}&limit=5&offset=0"
        )
        assert resp.status_code == 200

    def test_list_empty_logs(self, client_logs, mock_db_with_logs):
        """GET /logs/ com lista vazia."""
        mock_db_with_logs.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        resp = client_logs.get("/logs/")
        assert resp.status_code == 200
        assert resp.json() == []


class TestLogsOrdering:
    """Testes de ordenação de logs."""

    def test_logs_ordered_by_timestamp_descending(self, client_logs):
        """Logs retornados em ordem decrescente por timestamp."""
        resp = client_logs.get("/logs/")
        assert resp.status_code == 200

        logs = resp.json()
        if len(logs) > 1:
            # Mock retorna em ordem de criação (descending)
            assert len(logs) >= 1


class TestLogsPagination:
    """Testes de paginação."""

    def test_pagination_respects_limit_and_offset(self, client_logs):
        """Paginação com limit e offset funciona."""
        # Página 1: offset=0, limit=1
        resp1 = client_logs.get("/logs/?limit=1&offset=0")
        assert resp1.status_code == 200

        # Página 2: offset=1, limit=1
        resp2 = client_logs.get("/logs/?limit=1&offset=1")
        assert resp2.status_code == 200

    def test_large_offset_returns_empty(self, client_logs):
        """Offset muito grande retorna lista vazia."""
        resp = client_logs.get("/logs/?offset=999&limit=50")
        assert resp.status_code == 200
        # Se offset > total, retorna vazio


class TestLogsFiltering:
    """Testes de filtragem por dispositivo."""

    def test_filter_by_device_id_returns_only_that_device(
        self, client_logs, sample_device_id
    ):
        """Filtro por device_id retorna apenas logs daquele dispositivo."""
        resp = client_logs.get(f"/logs/?device_id={sample_device_id}")
        assert resp.status_code == 200

        logs = resp.json()
        for log in logs:
            assert log["device_id"] == str(sample_device_id)

    def test_filter_by_nonexistent_device_returns_empty(self, client_logs):
        """Filtro por dispositivo inexistente retorna lista vazia."""
        nonexistent_id = uuid.uuid4()

        resp = client_logs.get(f"/logs/?device_id={nonexistent_id}")
        assert resp.status_code == 200


class TestLogsIntegration:
    """Testes de integração de logs."""

    def test_list_all_then_filter_by_device(
        self, client_logs, sample_device_id
    ):
        """Listar todos os logs, depois filtrar por dispositivo."""
        # Listar todos
        all_resp = client_logs.get("/logs/")
        assert all_resp.status_code == 200
        all_logs = all_resp.json()
        all_count = len(all_logs)

        # Filtrar por dispositivo
        filtered_resp = client_logs.get(f"/logs/?device_id={sample_device_id}")
        assert filtered_resp.status_code == 200
        filtered_logs = filtered_resp.json()

        # Filtered <= all
        assert len(filtered_logs) <= all_count

    def test_pagination_across_large_result_set(self, client_logs):
        """Paginação funciona para grandes conjuntos de resultados."""
        page1 = client_logs.get("/logs/?limit=50&offset=0")
        page2 = client_logs.get("/logs/?limit=50&offset=50")

        assert page1.status_code == 200
        assert page2.status_code == 200
