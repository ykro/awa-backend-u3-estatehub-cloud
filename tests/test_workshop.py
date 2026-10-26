"""Taller guiado: JWT, barrera 401, guarda de dueño 403. En rojo en el starter."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.security import create_access_token, decode_access_token

ANA = ("ana@altamira.gt", "ana-pass-de-prueba")
CARLOS = ("carlos@veranda.gt", "carlos-pass-de-prueba")
SOFIA = ("admin@estatehub.gt", "sofia-pass-de-prueba")
TEST_SECRET = "pytest-only-secret-0123456789-abcdefghijklmnop"
OLD_PUBLIC_DEFAULT = "estatehub-2027-dev-secret-key-change-in-prod-32bytes!"

Login = Callable[[tuple[str, str]], dict[str, str]]


def _claims(token: str) -> dict:
    body = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


def _forge(secret: str = TEST_SECRET, **overrides: object) -> str:
    now = int(datetime.now(UTC).timestamp())
    payload: dict[str, object] = {
        "sub": "1",
        "role": "agent",
        "iat": now,
        "exp": now + 600,
        "iss": "estatehub-cloud",
        "aud": "estatehub-tests",
    }
    payload.update(overrides)
    payload = {k: v for k, v in payload.items() if v is not None}
    return jwt.encode(payload, secret, algorithm="HS256")


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ----- Paso 1: emitir y verificar el token -------------------------------------------


def test_create_and_decode_token_with_issuer_audience_and_numeric_subject() -> None:
    token = create_access_token(agent_id=7, role="admin")
    claims = _claims(token)
    assert claims["sub"] == "7"
    assert claims["role"] == "admin"
    assert claims["iss"] == "estatehub-cloud"
    assert claims["aud"] == "estatehub-tests"
    assert 0 < claims["exp"] - claims["iat"] <= 60 * 60
    assert decode_access_token(token)["sub"] == "7"


def test_decode_rejects_expired_forged_and_foreign_tokens() -> None:
    from app.security import AuthenticationError

    expired = create_access_token(agent_id=1, role="agent", expires_delta=timedelta(minutes=-5))
    bad_tokens = [
        expired,
        _forge(secret=OLD_PUBLIC_DEFAULT),
        _forge(aud="estatehub-de-otro-alumno"),
        _forge(aud=None),
        _forge(iss="otro-emisor"),
        _forge(exp=None),
        jwt.encode({"sub": "1", "role": "admin"}, None, algorithm="none"),
        "no-es-un-jwt",
    ]
    for bad in bad_tokens:
        with pytest.raises(AuthenticationError):
            decode_access_token(bad)


# ----- Paso 2: login sin enumeración ---------------------------------------------------


def test_login_issues_token_and_returns_public_agent(client: TestClient) -> None:
    ok = client.post("/api/v1/auth/token", json={"email": "  ANA@Altamira.GT ", "password": ANA[1]})
    assert ok.status_code == 200
    body = ok.json()
    assert body["token_type"] == "bearer"
    assert body["agent"] == {"id": 1, "name": "Ana Morales", "email": ANA[0], "role": "agent"}
    assert _claims(body["access_token"])["sub"] == "1"


def test_login_failures_look_identical_for_wrong_password_and_unknown_email(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    derivations: list[int] = []
    real_pbkdf2 = hashlib.pbkdf2_hmac

    def counting_pbkdf2(*args: object, **kwargs: object) -> bytes:
        derivations.append(1)
        return real_pbkdf2(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(hashlib, "pbkdf2_hmac", counting_pbkdf2)

    wrong = client.post("/api/v1/auth/token", json={"email": ANA[0], "password": "incorrecta-1"})
    derivations_wrong = len(derivations)
    unknown = client.post(
        "/api/v1/auth/token", json={"email": "nadie@estatehub.gt", "password": "incorrecta-1"}
    )
    derivations_unknown = len(derivations) - derivations_wrong

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong.headers["WWW-Authenticate"] == "Bearer"
    # Un correo inexistente también deriva un hash (señuelo): el tiempo no lo delata.
    assert derivations_wrong >= 1
    assert derivations_unknown >= 1


# ----- Paso 3: barrera de identidad (401) ---------------------------------------------


def test_protected_routes_require_a_valid_bearer_token(client: TestClient, login: Login) -> None:
    no_token = client.get("/api/v1/auth/me")
    assert no_token.status_code == 401
    assert no_token.json()["error"]["code"] == "INVALID_TOKEN"
    assert no_token.headers["WWW-Authenticate"] == "Bearer"

    assert client.get("/api/v1/agents").status_code == 401
    assert (
        client.get(
            "/api/v1/auth/me", headers=_bearer(_forge(secret=OLD_PUBLIC_DEFAULT))
        ).status_code
        == 401
    )
    assert client.get("/api/v1/auth/me", headers=_bearer(_forge(sub="999"))).status_code == 401
    assert client.get("/api/v1/auth/me", headers=_bearer(_forge(sub="ana"))).status_code == 401
    # Dígitos no ASCII ("٣" es isdigit) y un id de 30 dígitos: 401, nunca otro agente ni un 500.
    assert client.get("/api/v1/auth/me", headers=_bearer(_forge(sub="\u0663"))).status_code == 401
    assert client.get("/api/v1/auth/me", headers=_bearer(_forge(sub="1" * 30))).status_code == 401
    assert client.get("/api/v1/auth/me", headers=_bearer(_forge(aud="otro"))).status_code == 401

    me = client.get("/api/v1/auth/me", headers=login(ANA))
    assert me.status_code == 200
    assert me.json()["email"] == ANA[0]

    # Correos y roles del personal: solo admin (mínimo privilegio).
    not_admin = client.get("/api/v1/agents", headers=login(CARLOS))
    assert not_admin.status_code == 403
    assert not_admin.json()["error"]["code"] == "FORBIDDEN_ADMIN_ONLY"
    agents = client.get("/api/v1/agents", headers=login(SOFIA))
    assert agents.status_code == 200
    assert all("hashed_password" not in a for a in agents.json())


def test_create_property_takes_owner_from_token_and_validates_body(
    client: TestClient, login: Login
) -> None:
    headers = login(CARLOS)
    created = client.post(
        "/api/v1/properties",
        headers=headers,
        json={
            "title": "Casa  Lago   Atitlán",
            "city": "Panajachel",
            "price": 210_000,
            "bedrooms": 3,
        },
    )
    assert created.status_code == 201
    assert created.json()["owner_agent_id"] == 2
    assert created.json()["title"] == "Casa Lago Atitlán"

    spoofed = client.post(
        "/api/v1/properties",
        headers=headers,
        json={
            "title": "Casa ajena",
            "city": "Antigua",
            "price": 1,
            "bedrooms": 1,
            "owner_agent_id": 1,
        },
    )
    assert spoofed.status_code == 422
    too_expensive = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"title": "Castillo", "city": "Antigua", "price": 50_000_001, "bedrooms": 1},
    )
    assert too_expensive.status_code == 422
    blank = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"title": "      ", "city": "Antigua", "price": 1000, "bedrooms": 1},
    )
    assert blank.status_code == 422


# ----- Paso 4: guarda de dueño (403) en PATCH, DELETE y generate-pitch ----------------


def test_status_update_enforces_owner_or_admin(client: TestClient, login: Login) -> None:
    carlos = login(CARLOS)
    attack = client.patch("/api/v1/properties/1/status", headers=carlos, json={"status": "sold"})
    assert attack.status_code == 403
    assert attack.json()["error"]["code"] == "FORBIDDEN_NOT_OWNER"
    assert client.get("/api/v1/properties").json()[0]["status"] == "available"

    owner = client.patch(
        "/api/v1/properties/1/status", headers=login(ANA), json={"status": "reserved"}
    )
    assert owner.status_code == 200
    assert owner.json()["status"] == "reserved"

    admin = client.patch(
        "/api/v1/properties/3/status", headers=login(SOFIA), json={"status": "sold"}
    )
    assert admin.status_code == 200

    missing = client.patch("/api/v1/properties/99/status", headers=carlos, json={"status": "sold"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "PROPERTY_NOT_FOUND"

    # Entradas extremas: 422 con mensaje en español, nunca 500.
    huge = "99999999999999999999"
    for response in (
        client.patch(f"/api/v1/properties/{huge}/status", headers=carlos, json={"status": "sold"}),
        client.delete(f"/api/v1/properties/{huge}", headers=carlos),
        client.post(f"/api/v1/properties/{huge}/generate-pitch", headers=carlos),
    ):
        assert response.status_code == 422
        assert response.json()["error"]["details"]["errors"][0]["msg"].startswith("Debe ser")


def test_delete_enforces_owner_and_reports_missing(client: TestClient, login: Login) -> None:
    attack = client.delete("/api/v1/properties/2", headers=login(CARLOS))
    assert attack.status_code == 403
    assert len(client.get("/api/v1/properties").json()) == 3

    ana = login(ANA)
    assert client.delete("/api/v1/properties/2", headers=ana).status_code == 204
    again = client.delete("/api/v1/properties/2", headers=ana)
    assert again.status_code == 404
    assert client.delete("/api/v1/properties/2").status_code == 401


def test_generate_pitch_enforces_owner_and_persists_headline(
    client: TestClient, login: Login
) -> None:
    attack = client.post("/api/v1/properties/1/generate-pitch", headers=login(CARLOS))
    assert attack.status_code == 403
    assert client.get("/api/v1/properties").json()[0]["ai_pitch"] is None

    pitch = client.post("/api/v1/properties/1/generate-pitch", headers=login(ANA))
    assert pitch.status_code == 200
    data = pitch.json()
    assert data["property_id"] == 1
    assert data["source"] == "deterministic-fallback"
    assert len(data["highlights"]) == 3
    assert client.get("/api/v1/properties").json()[0]["ai_pitch"] == data["headline"]
