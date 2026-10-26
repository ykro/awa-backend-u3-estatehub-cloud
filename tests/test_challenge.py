"""Reto autónomo (tests públicos): protección contra fuerza bruta en el login.

El calificador corre además tests ocultos con más bordes y datos distintos.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

ANA = ("ana@altamira.gt", "ana-pass-de-prueba")
TOKEN_URL = "/api/v1/auth/token"


def _attempt(client: TestClient, email: str, password: str):
    return client.post(TOKEN_URL, json={"email": email, "password": password})


def test_sixth_attempt_is_blocked_with_429_even_with_correct_password(
    client: TestClient, clock
) -> None:
    for _ in range(5):
        failed = _attempt(client, ANA[0], "contrasena-equivocada")
        assert failed.status_code == 401
        clock.advance(10)

    blocked = _attempt(client, ANA[0], ANA[1])
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["error"]["code"] == "TOO_MANY_ATTEMPTS"
    # El primer fallo fue hace 50 s: faltan 900 - 50 = 850 s.
    assert blocked.headers["Retry-After"] == "850"
    assert body["error"]["details"]["retry_after_seconds"] == 850


def test_block_expires_when_the_window_ends(client: TestClient, clock) -> None:
    for _ in range(5):
        _attempt(client, ANA[0], "contrasena-equivocada")
    clock.advance(899)
    assert _attempt(client, ANA[0], ANA[1]).status_code == 429
    clock.advance(1)
    assert _attempt(client, ANA[0], ANA[1]).status_code == 200


def test_successful_login_before_the_block_resets_the_counter(client: TestClient, clock) -> None:
    for _ in range(4):
        assert _attempt(client, ANA[0], "contrasena-equivocada").status_code == 401
    assert _attempt(client, ANA[0], ANA[1]).status_code == 200
    # El contador volvió a cero: se necesitan otros cinco fallos para bloquear.
    for _ in range(5):
        assert _attempt(client, ANA[0], "contrasena-equivocada").status_code == 401
    assert _attempt(client, ANA[0], ANA[1]).status_code == 429


def test_unknown_emails_are_counted_and_blocked_the_same_way(client: TestClient, clock) -> None:
    ghost = "fantasma@estatehub.gt"
    for _ in range(5):
        assert _attempt(client, ghost, "lo-que-sea-123").status_code == 401
    blocked = _attempt(client, ghost, "lo-que-sea-123")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert blocked.headers["Retry-After"] == "900"
