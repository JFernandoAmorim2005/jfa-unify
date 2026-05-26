"""
Serviço de autenticação — geração e verificação de tokens HMAC-SHA256.
"""
import hashlib
import hmac
import secrets
import time
from typing import Any

from app.config import get_settings

settings = get_settings()


def generate_hmac_token(payload: dict[str, Any]) -> str:
    """
    Gera um token HMAC-SHA256 assinado com a SECRET_KEY.

    O token inclui timestamp de expiração para invalidação temporal.

    Args:
        payload: Dados a incluir no token (ex: {"tenant_id": "...", "device_id": "..."}).

    Returns:
        Token no formato: {dados_hex}.{hmac_hex}
    """
    expires_at = int(time.time()) + settings.token_expiry_seconds
    data = {**payload, "exp": expires_at}
    data_str = _dict_to_canonical_str(data)
    data_hex = data_str.encode().hex()
    signature = _sign(data_hex)
    return f"{data_hex}.{signature}"


def verify_hmac_token(token: str) -> dict[str, Any] | None:
    """
    Verifica um token HMAC-SHA256.

    Args:
        token: Token gerado por generate_hmac_token.

    Returns:
        Payload do token se válido e não expirado; None caso contrário.
    """
    try:
        data_hex, provided_sig = token.split(".", 1)
    except ValueError:
        return None

    expected_sig = _sign(data_hex)
    if not hmac.compare_digest(expected_sig, provided_sig):
        return None

    data_str = bytes.fromhex(data_hex).decode()
    payload = _canonical_str_to_dict(data_str)

    if int(time.time()) > payload.get("exp", 0):
        return None  # Token expirado

    return payload


def hash_pin(pin: str) -> str:
    """
    Gera hash HMAC-SHA256 de um PIN usando a SECRET_KEY.

    Args:
        pin: PIN em texto limpo (4-12 dígitos).

    Returns:
        Hash hexadecimal do PIN.
    """
    return _sign(pin)


def verify_pin(pin: str, stored_hash: str) -> bool:
    """
    Verifica se um PIN corresponde ao hash armazenado.

    Args:
        pin:         PIN em texto limpo.
        stored_hash: Hash previamente gerado por hash_pin.

    Returns:
        True se o PIN for correcto.
    """
    return hmac.compare_digest(hash_pin(pin), stored_hash)


def generate_nonce(length: int = 32) -> str:
    """Gera um nonce criptograficamente seguro."""
    return secrets.token_hex(length)


# --- Helpers internos ---

def _sign(data: str) -> str:
    """Assina dados com HMAC-SHA256 usando a SECRET_KEY."""
    return hmac.new(
        settings.secret_key.encode(),
        data.encode(),
        hashlib.sha256,
    ).hexdigest()


def _dict_to_canonical_str(data: dict) -> str:
    """Serialização determinística de dict para string."""
    return "&".join(f"{k}={v}" for k, v in sorted(data.items()))


def _canonical_str_to_dict(data_str: str) -> dict[str, Any]:
    """Deserialização de string canónica para dict."""
    result: dict[str, Any] = {}
    for pair in data_str.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            # Tentar converter para int (para "exp")
            try:
                result[k] = int(v)
            except ValueError:
                result[k] = v
    return result
