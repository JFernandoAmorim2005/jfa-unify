"""
Cliente HTTP para integração com JFA_Suite (módulo payaccess).

Responsabilidades:
  - Consultar saldo/usos disponíveis de um token pré-pago via GET /v1/tokens/{token_id}
  - Consumir 1 uso via POST /v1/tokens/{token_id}/usar (após grant de acesso confirmado)
  - Encapsular a comunicação HTTP de forma testável (injectável via FastAPI Depends)

A integração é opcional: o endpoint /access/validate funciona normalmente sem ela.
Para activar, definir SUITE_INTEGRATION_ENABLED=true e SUITE_BASE_URL no ambiente.

Modelo de saldo no JFA_Suite:
  - Não existe tabela "access_pay" — o saldo é representado por usos_restantes numa
    authorization (mode='prepaid_token') na tabela authorizations.
  - GET /v1/tokens/{id} → { "usos_restantes": int, "status": str, ... }
  - POST /v1/tokens/{id}/usar → { "acesso": "granted"|"denied", "usos_restantes": int }
"""
import logging
import uuid
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class SuiteClientError(Exception):
    """Erro base do cliente JFA_Suite."""


class SuiteTokenNotFound(SuiteClientError):
    """Token não encontrado no JFA_Suite (404)."""


class SuiteTokenInsufficient(SuiteClientError):
    """Token sem usos disponíveis ou expirado (409)."""


class SuiteClient:
    """
    Cliente HTTP para JFA_Suite payaccess API.

    Construído para ser injectável via FastAPI Depends:

        async def get_suite_client() -> SuiteClient:
            return SuiteClient()

    Em testes, substituir via dependency_overrides.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout: float | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.suite_base_url).rstrip("/")
        self._api_token = api_token or settings.suite_api_token
        self._timeout = timeout if timeout is not None else settings.suite_http_timeout

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        return headers

    async def get_token_balance(self, token_id: uuid.UUID) -> dict[str, Any]:
        """
        Consulta estado/saldo de um token pré-pago.

        Returns:
            dict com campos: token_id, status, usos_restantes, usos_max, usos_done,
            valido_ate, holder_ref.

        Raises:
            SuiteTokenNotFound: token não existe.
            SuiteClientError: erro de comunicação ou resposta inesperada.
        """
        url = f"{self._base_url}/v1/tokens/{token_id}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers=self._headers())
        except httpx.TimeoutException as exc:
            logger.warning("JFA_Suite timeout ao consultar saldo: %s", exc)
            raise SuiteClientError(f"Timeout na consulta de saldo: {exc}") from exc
        except httpx.RequestError as exc:
            logger.warning("JFA_Suite erro de rede: %s", exc)
            raise SuiteClientError(f"Erro de rede ao consultar JFA_Suite: {exc}") from exc

        if resp.status_code == 404:
            raise SuiteTokenNotFound(f"Token {token_id} não encontrado no JFA_Suite")
        if resp.status_code != 200:
            logger.error(
                "JFA_Suite resposta inesperada %d ao consultar %s",
                resp.status_code, url,
            )
            raise SuiteClientError(
                f"JFA_Suite devolveu status {resp.status_code} para GET {url}"
            )

        try:
            return resp.json()
        except Exception as exc:
            raise SuiteClientError(f"Resposta JSON inválida do JFA_Suite: {exc}") from exc

    async def consume_token(
        self,
        token_id: uuid.UUID,
        access_point_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Consome 1 uso do token pré-pago (após grant confirmado).

        Args:
            token_id:        UUID do token a consumir.
            access_point_id: UUID do access_point onde é utilizado.

        Returns:
            dict com campos: token_id, usos_restantes, valido_ate, acesso.

        Raises:
            SuiteTokenInsufficient: token esgotado ou expirado (409).
            SuiteTokenNotFound: token não existe (404).
            SuiteClientError: outro erro de comunicação.
        """
        url = f"{self._base_url}/v1/tokens/{token_id}/usar"
        body = {"access_point_id": str(access_point_id)}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=body, headers=self._headers())
        except httpx.TimeoutException as exc:
            logger.warning("JFA_Suite timeout ao consumir token: %s", exc)
            raise SuiteClientError(f"Timeout ao consumir token: {exc}") from exc
        except httpx.RequestError as exc:
            logger.warning("JFA_Suite erro de rede ao consumir token: %s", exc)
            raise SuiteClientError(f"Erro de rede ao consumir token: {exc}") from exc

        if resp.status_code == 404:
            raise SuiteTokenNotFound(f"Token {token_id} não encontrado ao consumir")
        if resp.status_code == 409:
            detail = resp.json().get("detail", "sem usos ou expirado")
            raise SuiteTokenInsufficient(
                f"Token {token_id} insuficiente: {detail}"
            )
        if resp.status_code not in (200, 201):
            raise SuiteClientError(
                f"JFA_Suite devolveu status {resp.status_code} ao consumir token {token_id}"
            )

        try:
            return resp.json()
        except Exception as exc:
            raise SuiteClientError(f"Resposta JSON inválida do JFA_Suite: {exc}") from exc

    def has_balance(self, token_data: dict[str, Any]) -> bool:
        """
        Verifica se um token tem saldo disponível (usos_restantes > 0 e status active).

        Args:
            token_data: dict retornado por get_token_balance().

        Returns:
            True se o token pode ser usado.
        """
        status = token_data.get("status", "")
        usos_restantes = token_data.get("usos_restantes", 0)
        return status == "active" and usos_restantes > 0


async def get_suite_client() -> SuiteClient:
    """
    FastAPI Dependency para injecção do SuiteClient.

    Uso:
        @router.post("/access/validate")
        async def validate_access(
            ...,
            suite_client: SuiteClient = Depends(get_suite_client),
        ): ...

    Em testes: substituir via app.dependency_overrides[get_suite_client].
    """
    return SuiteClient()
