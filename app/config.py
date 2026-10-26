"""Configuración tipada (12-Factor) validada al arrancar.

Si falta un valor obligatorio o es inseguro, el proceso no arranca: preferimos
fallar en el segundo 0 con un mensaje claro que servir tráfico con un secreto débil.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.validation_es import spanish_message

MIN_SECRET_LENGTH = 32
MIN_DEMO_PASSWORD_LENGTH = 12

# Valores de ejemplo conocidos (incluido el viejo default del repositorio).
# Cualquier secreto que aparezca en documentación pública debe considerarse comprometido.
KNOWN_EXAMPLE_SECRETS = frozenset(
    {
        "estatehub-2027-dev-secret-key-change-in-prod-32bytes!",
        "estatehub-2027-dev-secret-key-32bytes!",
        "reemplaza-con-un-secreto-generado",
        "change-me",
        "changeme",
        "secret",
        "secret123",
        "super-secret",
        "your-secret-key",
    }
)


class ConfigurationError(RuntimeError):
    """La configuración del entorno no permite arrancar la aplicación."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EstateHub Cloud API"
    service_name: str = "estatehub-cloud"
    owner: str = "local"
    # SHA del commit desplegado: deploy.yml lo pasa como COMMIT_SHA=${{ github.sha }}. /health lo
    # devuelve como "commit" (mismo contrato que el Curso 2); sin un SHA válido, null.
    commit_sha: str | None = None

    # Obligatorio y sin default: si falta, la aplicación no arranca.
    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_expire_minutes: int = Field(default=60, ge=1, le=1440)
    jwt_issuer: str = Field(default="estatehub-cloud", min_length=3)
    jwt_audience: str = Field(default="estatehub-local", min_length=3)

    # 600 000 iteraciones es la recomendación OWASP para PBKDF2-HMAC-SHA256.
    # Los tests la bajan con PASSWORD_HASH_ITERATIONS (ver tests/conftest.py).
    password_hash_iterations: int = Field(default=600_000, ge=1_000)

    # Lista blanca por entorno. En producción no hay orígenes por defecto.
    cors_origins: list[str] = Field(default_factory=list)

    database_url: str = "sqlite:///./estatehub_cloud.db"

    # Datos de demostración: solo con SEED_DEMO_DATA=true y contraseñas desde el entorno.
    seed_demo_data: bool = False
    demo_agent_password: SecretStr | None = None
    demo_admin_password: SecretStr | None = None

    # Protección contra fuerza bruta en el login (reto autónomo).
    login_max_attempts: int = Field(default=5, ge=1)
    login_window_seconds: int = Field(default=900, ge=1)

    # Extensión opcional con Gemini. Sin llave ni Vertex se usa el pitch determinista.
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: float = Field(default=8.0, gt=0, le=30)
    google_genai_use_vertexai: bool = False
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"

    @field_validator("jwt_secret_key")
    @classmethod
    def secret_must_be_strong(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if raw.strip().lower() in KNOWN_EXAMPLE_SECRETS:
            raise ValueError("JWT_SECRET_KEY usa un valor de ejemplo público; genera uno nuevo.")
        if len(raw) < MIN_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET_KEY debe tener al menos {MIN_SECRET_LENGTH} caracteres.")
        return value

    @field_validator("commit_sha", mode="before")
    @classmethod
    def commit_sha_or_none(cls, value: object) -> str | None:
        text = str(value or "").strip().lower()
        return text if re.fullmatch(r"[0-9a-f]{40}", text) else None

    @field_validator("cors_origins")
    @classmethod
    def no_wildcard_origin(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("CORS_ORIGINS no admite '*' porque la API acepta credenciales.")
        return value

    @model_validator(mode="after")
    def demo_passwords_required_when_seeding(self) -> Settings:
        if not self.seed_demo_data:
            return self
        for name in ("demo_agent_password", "demo_admin_password"):
            secret: SecretStr | None = getattr(self, name)
            if secret is None or len(secret.get_secret_value()) < MIN_DEMO_PASSWORD_LENGTH:
                raise ValueError(
                    f"SEED_DEMO_DATA=true exige {name.upper()} con al menos "
                    f"{MIN_DEMO_PASSWORD_LENGTH} caracteres."
                )
        return self


def load_settings() -> Settings:
    """Carga la configuración o detiene el arranque con un mensaje sin valores sensibles."""
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        problems = "\n".join(
            f"  - {'.'.join(str(p) for p in err['loc']).upper() or 'CONFIGURACIÓN'}: "
            f"{spanish_message(err)}"
            for err in exc.errors(include_input=False, include_url=False)
        )
        raise ConfigurationError(
            "No se puede arrancar EstateHub Cloud: configuración inválida.\n"
            f"{problems}\n"
            "Copia .env.example a .env y genera un secreto con:\n"
            '  uv run python -c "import secrets; print(secrets.token_urlsafe(48))"'
        ) from None


settings = load_settings()
