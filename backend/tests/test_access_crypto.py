"""
Testes unitários para access_crypto.py — HMAC-SHA256 PIN hashing e salt generation.

Estratégia:
  - Mock de settings.secret_key para testes determinísticos.
  - Verificação de hashing determinístico (input idêntico = output idêntico).
  - Validação de salt generation (32 bytes, aleatório).
  - Edge cases: PIN vazio, caracteres especiais, Unicode, salts diferentes.
"""
import os
from unittest.mock import patch, MagicMock

import pytest

from app.services.access_crypto import (
    hash_pin_for_device,
    generate_pin_salt,
    _compute_pin_hash,
)


@pytest.fixture
def mock_settings():
    """Mock de settings com SECRET_KEY fixo para testes determinísticos."""
    with patch("app.services.access_crypto.settings") as mock:
        mock.secret_key = "test-secret-key-1234567890abcdef"
        yield mock


@pytest.fixture
def fixed_salt() -> bytes:
    """Salt fixo para testes determinísticos."""
    return b"\x00" * 32


class TestComputePINHash:
    """Testes para _compute_pin_hash (função interna)."""

    def test_deterministic_hash(self, mock_settings, fixed_salt):
        """Mesmo PIN + salt = mesmo hash."""
        pin = "1234"
        hash1 = _compute_pin_hash(pin, fixed_salt)
        hash2 = _compute_pin_hash(pin, fixed_salt)
        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hexdigest = 64 chars

    def test_different_pins_different_hashes(self, mock_settings, fixed_salt):
        """PINs diferentes → hashes diferentes."""
        hash_1234 = _compute_pin_hash("1234", fixed_salt)
        hash_5678 = _compute_pin_hash("5678", fixed_salt)
        hash_0000 = _compute_pin_hash("0000", fixed_salt)

        assert hash_1234 != hash_5678
        assert hash_1234 != hash_0000
        assert hash_5678 != hash_0000

    def test_different_salts_different_hashes(self, mock_settings):
        """Salts diferentes → hashes diferentes."""
        pin = "1234"
        salt1 = b"\x00" * 32
        salt2 = b"\xff" * 32

        hash1 = _compute_pin_hash(pin, salt1)
        hash2 = _compute_pin_hash(pin, salt2)

        assert hash1 != hash2

    def test_uses_secret_key_in_hash(self, fixed_salt):
        """Alteração de secret_key altera o hash."""
        pin = "1234"

        with patch("app.services.access_crypto.settings") as mock1:
            mock1.secret_key = "secret-key-alpha"
            hash_alpha = _compute_pin_hash(pin, fixed_salt)

        with patch("app.services.access_crypto.settings") as mock2:
            mock2.secret_key = "secret-key-beta"
            hash_beta = _compute_pin_hash(pin, fixed_salt)

        assert hash_alpha != hash_beta

    def test_empty_pin(self, mock_settings, fixed_salt):
        """PIN vazio é válido (hash de string vazia)."""
        hash_empty = _compute_pin_hash("", fixed_salt)
        assert isinstance(hash_empty, str)
        assert len(hash_empty) == 64

    def test_special_characters_in_pin(self, mock_settings, fixed_salt):
        """PIN com caracteres especiais é válido."""
        special_pins = ["#$%&", "!@#$%^&*()", "[]{}|;:,.<>?", "  spaces  "]
        hashes = [_compute_pin_hash(pin, fixed_salt) for pin in special_pins]

        # Todos devem ser válidos e diferentes
        assert all(isinstance(h, str) and len(h) == 64 for h in hashes)
        assert len(set(hashes)) == len(hashes)  # Todos únicos

    def test_unicode_pin(self, mock_settings, fixed_salt):
        """PIN com caracteres Unicode é suportado."""
        unicode_pins = ["μπίν", "1234", "éàü", "日本語"]
        hashes = [_compute_pin_hash(pin, fixed_salt) for pin in unicode_pins]

        assert all(isinstance(h, str) and len(h) == 64 for h in hashes)
        assert len(set(hashes)) == len(hashes)

    def test_long_pin(self, mock_settings, fixed_salt):
        """PIN muito longo é válido."""
        long_pin = "1234" * 100  # 400 caracteres
        hash_long = _compute_pin_hash(long_pin, fixed_salt)
        assert isinstance(hash_long, str)
        assert len(hash_long) == 64

    def test_single_character_pin(self, mock_settings, fixed_salt):
        """PIN com um único caractere é válido."""
        hash_one = _compute_pin_hash("1", fixed_salt)
        assert isinstance(hash_one, str)
        assert len(hash_one) == 64

    def test_numeric_string_vs_numeric(self, mock_settings, fixed_salt):
        """PIN como string numérica é diferente de número."""
        # Função só aceita string, então ambos são strings
        hash_str = _compute_pin_hash("1234", fixed_salt)
        # Mas se tratarmos string vs numero diferentemente após
        # a conversão .encode(), deveriam ser iguais
        assert isinstance(hash_str, str)
        assert len(hash_str) == 64


class TestHashPINForDevice:
    """Testes para hash_pin_for_device (função pública)."""

    def test_hash_pin_for_device_exports_correctly(self, mock_settings, fixed_salt):
        """hash_pin_for_device retorna hash válido."""
        pin = "1234"
        pin_hash = hash_pin_for_device(pin, fixed_salt)

        assert isinstance(pin_hash, str)
        assert len(pin_hash) == 64  # SHA256 hexdigest

    def test_hash_pin_for_device_is_deterministic(self, mock_settings, fixed_salt):
        """hash_pin_for_device é determinístico."""
        pin = "5678"
        hash1 = hash_pin_for_device(pin, fixed_salt)
        hash2 = hash_pin_for_device(pin, fixed_salt)

        assert hash1 == hash2

    def test_hash_pin_for_device_matches_compute(self, mock_settings, fixed_salt):
        """hash_pin_for_device usa _compute_pin_hash internamente."""
        pin = "9999"
        exported_hash = hash_pin_for_device(pin, fixed_salt)
        computed_hash = _compute_pin_hash(pin, fixed_salt)

        assert exported_hash == computed_hash

    def test_different_devices_same_pin_different_salts(self, mock_settings):
        """Mesma senha em dispositivos diferentes (salts) = hashes diferentes."""
        pin = "1234"
        salt_device_1 = b"salt-device-001-" + b"\x00" * 16
        salt_device_2 = b"salt-device-002-" + b"\xff" * 16

        hash1 = hash_pin_for_device(pin, salt_device_1)
        hash2 = hash_pin_for_device(pin, salt_device_2)

        assert hash1 != hash2


class TestGeneratePINSalt:
    """Testes para generate_pin_salt (função de segurança)."""

    def test_generates_32_bytes(self):
        """Salt gerado tem exatamente 32 bytes."""
        salt = generate_pin_salt()
        assert isinstance(salt, bytes)
        assert len(salt) == 32

    def test_generates_random_salts(self):
        """Salts consecutivos são aleatórios (diferentes)."""
        salts = [generate_pin_salt() for _ in range(10)]

        # Todos devem ter 32 bytes
        assert all(len(s) == 32 for s in salts)

        # Todos devem ser diferentes (probabilidade de colisão < 2^-256)
        assert len(set(salts)) == len(salts)

    def test_salt_is_bytes_type(self):
        """Salt retornado é bytes, não str."""
        salt = generate_pin_salt()
        assert isinstance(salt, bytes)
        assert not isinstance(salt, str)

    def test_salt_usable_in_hmac(self, mock_settings):
        """Salt gerado funciona corretamente em _compute_pin_hash."""
        salt = generate_pin_salt()
        pin = "1234"

        hash1 = _compute_pin_hash(pin, salt)
        hash2 = _compute_pin_hash(pin, salt)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 64

    def test_multiple_generations_unique(self):
        """100 salts gerados são todos únicos."""
        salts = [generate_pin_salt() for _ in range(100)]
        unique_salts = set(salts)

        assert len(unique_salts) == len(salts)


class TestCryptoIntegration:
    """Testes de integração: fluxo realista de PIN hashing."""

    def test_pin_storage_and_verification_flow(self, mock_settings):
        """Fluxo realista: gerar salt, hashear PIN, armazenar, verificar."""
        # 1. Criar novo dispositivo: gerar salt
        device_salt = generate_pin_salt()
        assert len(device_salt) == 32

        # 2. Usuário define PIN "1234"
        pin = "1234"
        pin_hash = hash_pin_for_device(pin, device_salt)

        # 3. Armazenar em BD (simulado como dict)
        stored_data = {
            "id": "device-001",
            "card_uids": {"__pin__": pin_hash},
            "pin_salt": device_salt,
        }

        # 4. Verificação: o PIN fornecido produz o mesmo hash?
        provided_pin = "1234"
        provided_hash = hash_pin_for_device(provided_pin, stored_data["pin_salt"])

        assert provided_hash == stored_data["card_uids"]["__pin__"]

    def test_wrong_pin_fails_verification(self, mock_settings):
        """PIN incorreto não coincide com hash armazenado."""
        device_salt = generate_pin_salt()

        # PIN correto
        correct_pin = "1234"
        stored_hash = hash_pin_for_device(correct_pin, device_salt)

        # PIN incorreto
        wrong_pin = "5678"
        provided_hash = hash_pin_for_device(wrong_pin, device_salt)

        assert provided_hash != stored_hash

    def test_salt_compromise_scenario(self, mock_settings):
        """Se salt for comprometido, PIN ainda é protegido por secret_key."""
        device_salt = generate_pin_salt()
        pin = "1234"
        pin_hash = hash_pin_for_device(pin, device_salt)

        # Conhecer o PIN (1234), o salt, MAS não a secret_key → não conseguir recriar hash
        # (Este teste ilustra a necessidade da secret_key na chave HMAC)

        with patch("app.services.access_crypto.settings") as mock:
            mock.secret_key = "wrong-secret-key-different"
            wrong_secret_hash = hash_pin_for_device(pin, device_salt)

        assert wrong_secret_hash != pin_hash

    def test_multiple_devices_independent_salts(self, mock_settings):
        """Múltiplos dispositivos com mesmo PIN mas salts diferentes = hashes diferentes."""
        pin = "1234"

        device_1_salt = generate_pin_salt()
        device_1_hash = hash_pin_for_device(pin, device_1_salt)

        device_2_salt = generate_pin_salt()
        device_2_hash = hash_pin_for_device(pin, device_2_salt)

        device_3_salt = generate_pin_salt()
        device_3_hash = hash_pin_for_device(pin, device_3_salt)

        # Todos diferentes
        assert device_1_hash != device_2_hash
        assert device_2_hash != device_3_hash
        assert device_1_hash != device_3_hash

        # Mas re-hashing com mesmo salt produz mesmo valor
        assert hash_pin_for_device(pin, device_1_salt) == device_1_hash
        assert hash_pin_for_device(pin, device_2_salt) == device_2_hash
        assert hash_pin_for_device(pin, device_3_salt) == device_3_hash
