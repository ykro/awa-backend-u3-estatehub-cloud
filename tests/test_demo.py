"""Demo: lo que el starter ya cumple. Deben pasar desde el primer día."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings


def test_demo_health_catalog_and_console_are_safe_by_default(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    # Contrato de /health (igual que el Curso 2): commit es null en local; en Cloud Run,
    # deploy.yml inyecta COMMIT_SHA con el SHA de 40 caracteres del commit desplegado.
    assert health.json() == {
        "status": "ok",
        "service": "estatehub-cloud",
        "owner": "local",
        "commit": None,
    }
    assert health.headers["X-Content-Type-Options"] == "nosniff"
    assert health.headers["Referrer-Policy"] == "no-referrer"

    catalog = client.get("/api/v1/properties")
    assert catalog.status_code == 200
    items = catalog.json()
    assert [p["id"] for p in items] == [1, 2, 3]
    for item in items:
        assert "owner_agent_email" not in item
        assert "hashed_password" not in item
    assert "@" not in catalog.text

    console = client.get("/")
    assert console.status_code == 200
    csp = console.headers["Content-Security-Policy"]
    nonce = re.search(r"script-src 'nonce-([A-Za-z0-9_-]+)'", csp)
    assert nonce is not None
    assert "default-src 'none'" in csp and "frame-ancestors 'none'" in csp
    assert f'<script nonce="{nonce.group(1)}">' in console.text
    assert "cdn.tailwindcss.com" not in console.text
    assert ".innerHTML" not in console.text
    assert "onclick=" not in console.text
    assert "pass-de-prueba" not in console.text


def test_demo_validation_errors_and_settings_fail_fast(client: TestClient) -> None:
    # Una contraseña de 7 caracteres viola min_length=8: el error crudo de Pydantic la
    # repetiría en "input". El envelope solo puede traer loc, msg y type.
    short_password = "Clave-7"
    bad_login = client.post(
        "/api/v1/auth/token", json={"email": "ana@altamira.gt", "password": short_password}
    )
    assert bad_login.status_code == 422
    assert bad_login.json()["error"]["code"] == "VALIDATION_ERROR"
    assert short_password not in bad_login.text
    for err in bad_login.json()["error"]["details"]["errors"]:
        assert set(err) == {"loc", "msg", "type"}
    # Mensajes de validación en español.
    assert bad_login.json()["error"]["details"]["errors"][0]["msg"] == (
        "Debe tener al menos 8 caracteres"
    )

    secret_password = "NoDebeVolver-123"
    extra_field = client.post(
        "/api/v1/auth/token",
        json={"email": "ana@altamira.gt", "password": secret_password, "role": "admin"},
    )
    assert extra_field.status_code == 422
    assert secret_password not in extra_field.text

    sha = "0123456789abcdef0123456789abcdef01234567"
    deployed = Settings(_env_file=None, jwt_secret_key="x" * 40, commit_sha=sha.upper())  # type: ignore[call-arg]
    assert deployed.commit_sha == sha
    for not_a_sha in ("", "main", sha[:12]):
        other = Settings(_env_file=None, jwt_secret_key="x" * 40, commit_sha=not_a_sha)  # type: ignore[call-arg]
        assert other.commit_sha is None

    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret_key="corto")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Settings(  # type: ignore[call-arg]
            _env_file=None,
            jwt_secret_key="estatehub-2027-dev-secret-key-change-in-prod-32bytes!",
        )
    with pytest.raises(ValidationError):
        Settings(  # type: ignore[call-arg]
            _env_file=None,
            jwt_secret_key="x" * 40,
            seed_demo_data=True,
            demo_agent_password=None,
            demo_admin_password=None,
        )

    # Errores que genera el framework (ruta inexistente, método, cuerpo no UTF-8): mismo sobre.
    missing = client.get("/api/v1/no-existe")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    assert missing.json()["error"]["message"] == "La ruta solicitada no existe."

    wrong_method = client.put("/health")
    assert wrong_method.status_code == 405
    assert wrong_method.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in wrong_method.headers["allow"]

    not_utf8 = client.post(
        "/api/v1/auth/token",
        content=b"\xff\xfe",
        headers={"Content-Type": "application/json"},
    )
    assert not_utf8.status_code == 422
    assert not_utf8.json()["error"]["code"] == "VALIDATION_ERROR"
