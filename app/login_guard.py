"""Protección contra fuerza bruta en POST /api/v1/auth/token (reto autónomo).

La especificación completa (contrato HTTP, ventana, cabeceras y casos borde) está en
README.md. Este archivo fija lo único que los tests necesitan encontrar:

- get_clock(): dependencia que devuelve el reloj. Los tests la reemplazan por un reloj
  falso para avanzar el tiempo sin dormir. Toda lectura de tiempo del reto debe salir de
  aquí (nada de time.time() dentro de la lógica).
- get_login_guard(): dependencia que devuelve el limitador. Los tests la reemplazan por
  LoginAttemptGuard(max_attempts=5, window_seconds=900) nuevo en cada test.
- LoginAttemptGuard(max_attempts, window_seconds): el constructor debe aceptar esos dos
  argumentos con nombre. El resto del diseño (métodos, estructuras) es tuyo.

Cuidado con la concurrencia: varias peticiones llegan en hilos distintos. "Consultar si está
bloqueado" y "registrar el fallo" con la verificación de la contraseña en medio no es atómico.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from app.config import settings

Clock = Callable[[], float]


def system_clock() -> float:
    """Reloj monotónico en segundos (no retrocede si cambia la hora del sistema)."""
    return time.monotonic()


class LoginAttemptGuard:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # TODO (reto autónomo): estado en memoria y métodos para consultar el bloqueo,
        # registrar fallos y registrar éxitos.


_guard = LoginAttemptGuard(
    max_attempts=settings.login_max_attempts,
    window_seconds=settings.login_window_seconds,
)


def get_login_guard() -> LoginAttemptGuard:
    """Dependencia de FastAPI. Los tests la reemplazan por una instancia nueva por test."""
    return _guard


def get_clock() -> Clock:
    """Dependencia de FastAPI. Los tests la reemplazan por un reloj falso controlable."""
    return system_clock
