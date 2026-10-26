from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any

import jwt

from app.config import settings

HASH_SCHEME = "pbkdf2_sha256"
REQUIRED_CLAIMS = ["sub", "role", "iat", "exp", "iss", "aud"]


class AuthenticationError(Exception):
    """Falla de identidad: se traduce a HTTP 401."""

    def __init__(self, message: str, code: str = "INVALID_TOKEN") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ForbiddenOwnerError(Exception):
    """Identidad válida sin permiso sobre el recurso: se traduce a HTTP 403."""

    def __init__(self, property_id: int) -> None:
        super().__init__(f"No tienes permiso para modificar el inmueble #{property_id}.")
        self.property_id = property_id


def normalize_email(raw_email: str) -> str:
    """Forma canónica de un correo: sin espacios en los extremos y en minúsculas."""
    return raw_email.strip().lower()


def hash_password(plain_password: str, *, iterations: int | None = None) -> str:
    """PBKDF2-HMAC-SHA256 con sal aleatoria de 16 bytes por contraseña."""
    rounds = iterations or settings.password_hash_iterations
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), rounds
    ).hex()
    return f"{HASH_SCHEME}${rounds}${salt}${derived}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Recalcula la derivación con la sal guardada y compara en tiempo constante."""
    try:
        scheme, rounds, salt, expected_hex = stored_hash.split("$", 3)
        if scheme != HASH_SCHEME:
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), int(rounds)
        ).hex()
    except ValueError:
        return False
    return hmac.compare_digest(derived, expected_hex)


@cache
def decoy_password_hash() -> str:
    """Hash señuelo: se verifica cuando el correo no existe para igualar el tiempo de respuesta."""
    return hash_password(secrets.token_urlsafe(24))


def create_access_token(
    *,
    agent_id: int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """TODO (taller, paso 2): firma un JWT HS256.

    Claims obligatorios: sub (str(agent_id)), role, iat, exp, iss (settings.jwt_issuer)
    y aud (settings.jwt_audience). Si expires_delta es None, la vigencia es
    settings.jwt_expire_minutes. La llave sale de settings.jwt_secret_key.get_secret_value().
    """
    _ = (agent_id, role, expires_delta, datetime, UTC, Any, jwt)
    raise NotImplementedError("Taller, paso 2: implementa create_access_token")


def decode_access_token(token: str) -> dict[str, Any]:
    """TODO (taller, paso 2): verifica firma, algoritmo, exp, iss y aud.

    Usa jwt.decode con algorithms=[settings.jwt_algorithm], audience, issuer y
    options={"require": REQUIRED_CLAIMS}. Cualquier error de PyJWT se convierte en
    AuthenticationError (401); el token expirado con un mensaje propio.
    """
    _ = token
    raise NotImplementedError("Taller, paso 2: implementa decode_access_token")
