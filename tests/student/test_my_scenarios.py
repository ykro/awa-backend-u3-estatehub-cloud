"""Tus tests propios (al menos 2).

Tus tests propios suman si pasan contra la solución de referencia y detectan mutantes que la
suite pública no detecta (errores sembrados en el reto). Reescribir un test
público no suma.
Usa los fixtures de tests/conftest.py: client, clock, login y, para peticiones simultáneas con
hilos, file_client. No agregues conftest.py aquí.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_my_scenario_1(client: TestClient) -> None:
    _ = client
    pytest.fail("Escribe un escenario que detecte un error de autorización o de autenticación.")


def test_my_scenario_2(client: TestClient) -> None:
    _ = client
    pytest.fail("Escribe un escenario de borde del reto (ventana, normalización o reinicio).")
