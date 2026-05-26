"""
Utilitários criptográficos para validação de acesso (PIN, cartão).
Sem dependência de modelos ORM ou BD.
"""
import hashlib
import hmac
import os

from app.config import get_settings

settings = get_settings()


def _compute_pin_hash(pin: str, salt: bytes) -> str:
    """
    Gera hash HMAC-SHA256 do PIN usando o salt do dispositivo.
    Usa a SECRET_KEY da aplicação como chave HMAC adicional.
    """
    key = settings.secret_key.encode() + salt
    return hmac.new(key, pin.encode(), hashlib.sha256).hexdigest()


def hash_pin_for_device(pin: str, salt: bytes) -> str:
    """Exporta o hash do PIN para armazenamento em card_uids['__pin__']."""
    return _compute_pin_hash(pin, salt)


def generate_pin_salt() -> bytes:
    """Gera salt criptograficamente seguro de 32 bytes."""
    return os.urandom(32)
