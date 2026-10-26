"""Fixtures oficiales: herméticos (sin archivos .db, sin red) y deterministas.

Este archivo es parte de la suite oficial. No lo modifiques: el calificador usa su
propia copia.
"""

from __future__ import annotations

import os

# La configuración se fija ANTES de importar la app: Settings se valida al importar.
# Secreto exclusivo de pruebas (no es una credencial; nunca se usa fuera de pytest).
os.environ["JWT_SECRET_KEY"] = "pytest-only-secret-0123456789-abcdefghijklmnop"
os.environ["JWT_ISSUER"] = "estatehub-cloud"
os.environ["JWT_AUDIENCE"] = "estatehub-tests"
# Base en memoria: ningún test crea archivos .db.
os.environ["DATABASE_URL"] = "sqlite://"
# Sin datos de demostración: cada test crea sus propios agentes.
os.environ["SEED_DEMO_DATA"] = "false"
# Iteraciones bajas SOLO en pruebas para que la suite corra rápido.
# En producción el default es 600 000 (app/config.py).
os.environ["PASSWORD_HASH_ITERATIONS"] = "1000"
# Sin Gemini: ninguna prueba llama a la red.
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'
os.environ["LOGIN_MAX_ATTEMPTS"] = "5"
os.environ["LOGIN_WINDOW_SECONDS"] = "900"
os.environ.pop("OWNER", None)
os.environ.pop("COMMIT_SHA", None)

from collections.abc import Callable, Generator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.database import get_session  # noqa: E402
from app.login_guard import LoginAttemptGuard, get_clock, get_login_guard  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Agent, Property  # noqa: E402
from app.security import hash_password  # noqa: E402

# Credenciales ficticias de prueba, creadas solo dentro de la base en memoria.
ANA = ("ana@altamira.gt", "ana-pass-de-prueba")
CARLOS = ("carlos@veranda.gt", "carlos-pass-de-prueba")
SOFIA = ("admin@estatehub.gt", "sofia-pass-de-prueba")

ANA_ID, CARLOS_ID, SOFIA_ID = 1, 2, 3
ANA_PROPERTY, ANA_SECOND_PROPERTY, CARLOS_PROPERTY = 1, 2, 3


class FakeClock:
    """Reloj controlable: los tests avanzan el tiempo sin dormir."""

    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _seed(session: Session) -> None:
    session.add_all(
        [
            Agent(name="Ana Morales", email=ANA[0], hashed_password=hash_password(ANA[1])),
            Agent(name="Carlos Vega", email=CARLOS[0], hashed_password=hash_password(CARLOS[1])),
            Agent(
                name="Sofía Directora",
                email=SOFIA[0],
                hashed_password=hash_password(SOFIA[1]),
                role="admin",
            ),
        ]
    )
    session.commit()
    session.add_all(
        [
            Property(
                owner_agent_id=ANA_ID,
                title="Penthouse Vista Volcán de Agua",
                city="Antigua Guatemala",
                price=395_000,
                bedrooms=3,
            ),
            Property(
                owner_agent_id=ANA_ID,
                title="Loft Botánico Zona 14",
                city="Ciudad de Guatemala",
                price=245_000,
                bedrooms=2,
            ),
            Property(
                owner_agent_id=CARLOS_ID,
                title="Villa Jardín Las Luces",
                city="Santa Catarina Pinula",
                price=480_000,
                bedrooms=4,
                status="reserved",
            ),
        ]
    )
    session.commit()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def _client_for(engine: Engine, clock: FakeClock) -> Generator[TestClient]:
    """TestClient con la base, el limitador y el reloj de este test."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        _seed(session)

    def override_session() -> Generator[Session]:
        with Session(engine) as session:
            yield session

    guard = LoginAttemptGuard(max_attempts=5, window_seconds=900)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_login_guard] = lambda: guard
    app.dependency_overrides[get_clock] = lambda: clock
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(clock: FakeClock) -> Generator[TestClient]:
    """Base en memoria con una sola conexión compartida (StaticPool): rápida y sin archivos.

    No sirve para tests con hilos: una conexión sqlite3 no se comparte entre hilos.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield from _client_for(engine, clock)


@pytest.fixture
def file_client(clock: FakeClock, tmp_path: Path) -> Generator[TestClient]:
    """Base SQLite sobre un archivo temporal fuera del repositorio: una conexión por hilo.

    Úsalo en tests con peticiones simultáneas (por ejemplo, ráfagas de login con hilos).
    """
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrencia.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    yield from _client_for(engine, clock)


@pytest.fixture
def login(client: TestClient) -> Callable[[tuple[str, str]], dict[str, str]]:
    """Inicia sesión y devuelve el encabezado Authorization listo para usar."""

    def _login(credentials: tuple[str, str]) -> dict[str, str]:
        email, password = credentials
        response = client.post("/api/v1/auth/token", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login
