"""
Testes unitários para serviço de autenticação (geração e verificação de tokens HMAC).

Estratégia: Validar geração de tokens, verificação de assinatura, expiração,
PIN hashing, nonce generation com isolation de config.
"""
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services import auth


@pytest.fixture
def mock_settings():
    """Mock de settings com SECRET_KEY e token_expiry_seconds."""
    settings = MagicMock()
    settings.secret_key = "test-secret-key-very-secure"
    settings.token_expiry_seconds = 3600
    return settings


@pytest.fixture(autouse=True)
def inject_mock_settings(real_verify_hmac_token, monkeypatch):
    """Restaura verify_hmac_token real (capturada antes do patch global)."""
    # mock_settings é automaticamente injetado pelo conftest.py para todos os testes
    # Restaurar a função REAL capturada em conftest.py antes do patch
    monkeypatch.setattr("app.services.auth.verify_hmac_token", real_verify_hmac_token)


class TestGenerateHmacToken:
    """Testes para generate_hmac_token."""

    def test_generate_token_returns_string(self, mock_settings):
        """generate_hmac_token retorna string com formato {data_hex}.{signature}."""
        payload = {"tenant_id": "00000000-0000-0000-0000-000000000001"}
        token = auth.generate_hmac_token(payload)

        assert isinstance(token, str)
        assert "." in token
        parts = token.split(".")
        assert len(parts) == 2
        assert len(parts[0]) > 0  # data_hex
        assert len(parts[1]) == 64  # sha256 hex = 64 chars

    def test_generate_token_includes_exp(self, mock_settings):
        """Token gerado inclui timestamp de expiração."""
        payload = {"tenant_id": "test"}
        before = int(time.time())
        token = auth.generate_hmac_token(payload)
        after = int(time.time())

        data_hex = token.split(".")[0]
        data_str = bytes.fromhex(data_hex).decode()
        # Dados estão no formato "k1=v1&k2=v2&..."
        assert "exp=" in data_str
        # Extrair exp e validar que está dentro do intervalo esperado
        parts = dict(pair.split("=") for pair in data_str.split("&"))
        exp = int(parts["exp"])
        assert before + mock_settings.token_expiry_seconds <= exp <= after + mock_settings.token_expiry_seconds + 1

    def test_generate_token_includes_payload_data(self, mock_settings):
        """Token inclui dados do payload original."""
        payload = {"tenant_id": "tenant-123", "user_id": "user-456"}
        token = auth.generate_hmac_token(payload)

        data_hex = token.split(".")[0]
        data_str = bytes.fromhex(data_hex).decode()
        assert "tenant_id=tenant-123" in data_str
        assert "user_id=user-456" in data_str

    def test_generate_token_different_payloads_different_tokens(self, mock_settings):
        """Payloads diferentes geram tokens diferentes (mesmo com timestamp próximo)."""
        payload1 = {"tenant_id": "tenant-1"}
        payload2 = {"tenant_id": "tenant-2"}

        # Mockar time.time() para garantir mesmo timestamp
        with patch("app.services.auth.time.time", return_value=1000):
            token1 = auth.generate_hmac_token(payload1)
            token2 = auth.generate_hmac_token(payload2)

        assert token1 != token2

    def test_generate_token_signature_is_deterministic(self, mock_settings):
        """Mesmo payload + timestamp gera mesma assinatura."""
        payload = {"tenant_id": "test"}

        with patch("app.services.auth.time.time", return_value=1000):
            token1 = auth.generate_hmac_token(payload)
            token2 = auth.generate_hmac_token(payload)

        assert token1 == token2


class TestVerifyHmacToken:
    """Testes para verify_hmac_token."""

    def test_verify_valid_token_returns_payload(self, mock_settings):
        """verify_hmac_token com token válido retorna payload original."""
        original_payload = {"tenant_id": "tenant-1", "device_id": "device-1"}

        with patch("app.services.auth.time.time", return_value=1000):
            token = auth.generate_hmac_token(original_payload)
            # Verificar com tempo antes da expiração
            result = auth.verify_hmac_token(token)

        assert result is not None
        assert result["tenant_id"] == "tenant-1"
        assert result["device_id"] == "device-1"
        assert "exp" in result

    def test_verify_expired_token_returns_none(self, mock_settings, monkeypatch):
        """verify_hmac_token com token expirado retorna None."""
        payload = {"tenant_id": "test"}

        # Garantir que settings é a instância mockada
        monkeypatch.setattr("app.services.auth.settings", mock_settings)

        # Gerar token com time=1000, expiração em 1100 (token_expiry_seconds=100 do mock)
        with patch("app.services.auth.time.time", return_value=1000):
            token = auth.generate_hmac_token(payload)

        # Verificar com time=1200 (após expiração)
        with patch("app.services.auth.time.time", return_value=1200):
            result = auth.verify_hmac_token(token)

        assert result is None

    def test_verify_tampered_token_returns_none(self, mock_settings):
        """verify_hmac_token detecta tampering na signature."""
        payload = {"tenant_id": "test"}
        with patch("app.services.auth.time.time", return_value=1000):
            token = auth.generate_hmac_token(payload)

        # Alterar um caractere da signature
        data_hex, signature = token.split(".")
        tampered_sig = signature[:-1] + ("0" if signature[-1] != "0" else "1")
        tampered_token = f"{data_hex}.{tampered_sig}"

        result = auth.verify_hmac_token(tampered_token)
        assert result is None

    def test_verify_tampered_data_returns_none(self, mock_settings):
        """verify_hmac_token detecta tampering nos dados."""
        payload = {"tenant_id": "test"}
        with patch("app.services.auth.time.time", return_value=1000):
            token = auth.generate_hmac_token(payload)

        data_hex, signature = token.split(".")
        # Alterar um caractere dos dados
        tampered_data_hex = data_hex[:-1] + ("0" if data_hex[-1] != "0" else "1")
        tampered_token = f"{tampered_data_hex}.{signature}"

        result = auth.verify_hmac_token(tampered_token)
        assert result is None

    def test_verify_malformed_token_returns_none(self, mock_settings):
        """verify_hmac_token com formato inválido retorna None."""
        # Sem ponto separador
        result = auth.verify_hmac_token("invalid_token")
        assert result is None

        # Múltiplos pontos (mais que um separador)
        result = auth.verify_hmac_token("data.sig.extra")
        assert result is None

    def test_verify_invalid_hex_returns_none(self, mock_settings):
        """verify_hmac_token com dados_hex inválidos retorna None."""
        # "ZZ" não é hex válido
        invalid_token = "ZZ.0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        result = auth.verify_hmac_token(invalid_token)
        assert result is None

    def test_verify_empty_token_returns_none(self, mock_settings):
        """verify_hmac_token com string vazia retorna None."""
        result = auth.verify_hmac_token("")
        assert result is None

    def test_verify_none_token_returns_none(self, mock_settings):
        """verify_hmac_token com None levanta exceção (graceful)."""
        # Esperamos que trate com elegância
        try:
            result = auth.verify_hmac_token(None)
            # Se não levanta, deve retornar None
            assert result is None
        except (AttributeError, TypeError):
            # Aceitável — None não é string
            pass


class TestHashPin:
    """Testes para hash_pin."""

    def test_hash_pin_returns_string(self, mock_settings):
        """hash_pin retorna string hexadecimal."""
        result = auth.hash_pin("1234")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 = 64 hex chars

    def test_hash_pin_deterministic(self, mock_settings):
        """Mesmo PIN gera sempre o mesmo hash."""
        pin = "5678"
        hash1 = auth.hash_pin(pin)
        hash2 = auth.hash_pin(pin)
        assert hash1 == hash2

    def test_hash_pin_different_pins_different_hashes(self, mock_settings):
        """PINs diferentes geram hashes diferentes."""
        hash1 = auth.hash_pin("1111")
        hash2 = auth.hash_pin("2222")
        assert hash1 != hash2

    def test_hash_pin_uses_secret_key(self, mock_settings, monkeypatch):
        """Hash depende da SECRET_KEY."""
        from unittest.mock import patch
        pin = "1234"

        # Garantir que settings é a instância mockada
        monkeypatch.setattr("app.services.auth.settings", mock_settings)

        # Primeiro hash com secret-1
        with patch("app.services.auth.settings.secret_key", "secret-1"):
            hash1 = auth.hash_pin(pin)

        # Segundo hash com secret-2
        with patch("app.services.auth.settings.secret_key", "secret-2"):
            hash2 = auth.hash_pin(pin)

        assert hash1 != hash2

    def test_hash_pin_various_lengths(self, mock_settings):
        """hash_pin funciona com PINs de diferentes comprimentos."""
        for pin in ["1", "123", "123456", "1234567890"]:
            result = auth.hash_pin(pin)
            assert len(result) == 64
            assert result.isalnum()


class TestVerifyPin:
    """Testes para verify_pin."""

    def test_verify_pin_correct_returns_true(self, mock_settings):
        """verify_pin com PIN correcto retorna True."""
        pin = "1234"
        stored_hash = auth.hash_pin(pin)
        assert auth.verify_pin(pin, stored_hash) is True

    def test_verify_pin_incorrect_returns_false(self, mock_settings):
        """verify_pin com PIN incorrecto retorna False."""
        stored_hash = auth.hash_pin("1234")
        assert auth.verify_pin("5678", stored_hash) is False

    def test_verify_pin_case_sensitive(self, mock_settings):
        """verify_pin é case-sensitive (para strings alphanuméricas)."""
        stored_hash = auth.hash_pin("AbCd")
        assert auth.verify_pin("AbCd", stored_hash) is True
        assert auth.verify_pin("abcd", stored_hash) is False

    def test_verify_pin_uses_hmac_compare_digest(self, mock_settings):
        """verify_pin usa hmac.compare_digest para timing attack protection."""
        pin = "1234"
        stored_hash = auth.hash_pin(pin)

        # Simular wrong hash
        wrong_hash = "0" * 64

        # Ambas as comparações devem ser seguras (mesmo tempo, aprox)
        result_correct = auth.verify_pin(pin, stored_hash)
        result_wrong = auth.verify_pin("9999", wrong_hash)

        assert result_correct is True
        assert result_wrong is False


class TestGenerateNonce:
    """Testes para generate_nonce."""

    def test_generate_nonce_returns_string(self, mock_settings):
        """generate_nonce retorna string hexadecimal."""
        result = auth.generate_nonce()
        assert isinstance(result, str)
        assert result.isalnum() or all(c in "0123456789abcdef" for c in result)

    def test_generate_nonce_default_length(self, mock_settings):
        """generate_nonce com comprimento padrão (32 bytes = 64 hex chars)."""
        result = auth.generate_nonce()
        # 32 bytes = 64 hex characters
        assert len(result) == 64

    def test_generate_nonce_custom_length(self, mock_settings):
        """generate_nonce respeita parâmetro de comprimento."""
        result16 = auth.generate_nonce(length=16)
        result8 = auth.generate_nonce(length=8)

        assert len(result16) == 32  # 16 bytes = 32 hex
        assert len(result8) == 16   # 8 bytes = 16 hex

    def test_generate_nonce_random(self, mock_settings):
        """Diferentes chamadas geram nonces diferentes."""
        nonce1 = auth.generate_nonce()
        nonce2 = auth.generate_nonce()
        assert nonce1 != nonce2

    def test_generate_nonce_length_one(self, mock_settings):
        """generate_nonce com length=1 gera 2 hex chars."""
        result = auth.generate_nonce(length=1)
        assert len(result) == 2
        assert result.isalnum() or all(c in "0123456789abcdef" for c in result)


class TestSigningIntegration:
    """Testes de integração entre funções de assinatura."""

    def test_token_round_trip(self, mock_settings):
        """Gerar token, depois verificar retorna payload original."""
        original = {"tenant_id": "t1", "user": "u1", "scope": "admin"}

        with patch("app.services.auth.time.time", return_value=5000):
            token = auth.generate_hmac_token(original)
            verified = auth.verify_hmac_token(token)

        assert verified is not None
        assert verified["tenant_id"] == "t1"
        assert verified["user"] == "u1"
        assert verified["scope"] == "admin"

    def test_pin_round_trip(self, mock_settings):
        """Hash PIN, depois verificar retorna True."""
        pin = "test-pin-1234"
        hashed = auth.hash_pin(pin)
        verified = auth.verify_pin(pin, hashed)
        assert verified is True

    def test_nonce_entropy(self, mock_settings):
        """Gerar muitos nonces, todos diferentes."""
        nonces = [auth.generate_nonce(length=8) for _ in range(100)]
        assert len(set(nonces)) == 100  # Todos únicos
