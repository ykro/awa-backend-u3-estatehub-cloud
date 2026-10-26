from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import settings
from app.models import Agent, Property
from app.security import hash_password

logger = logging.getLogger("estatehub.database")

# check_same_thread es un argumento solo de SQLite (FastAPI atiende rutas en varios hilos).
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)


def init_db(target_engine: Engine = engine) -> None:
    SQLModel.metadata.create_all(target_engine)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session


def seed_demo_data(session: Session) -> bool:
    """Siembra agentes e inmuebles de demostración.

    Solo corre con SEED_DEMO_DATA=true. Las contraseñas salen de DEMO_AGENT_PASSWORD y
    DEMO_ADMIN_PASSWORD (sin default, validadas en Settings). En Cloud Run no se activa.
    """
    if not settings.seed_demo_data:
        return False
    if session.exec(select(Agent)).first() is not None:
        return False
    assert settings.demo_agent_password is not None
    assert settings.demo_admin_password is not None
    agent_password = settings.demo_agent_password.get_secret_value()
    admin_password = settings.demo_admin_password.get_secret_value()

    ana = Agent(
        name="Ana Morales",
        email="ana@altamira.gt",
        hashed_password=hash_password(agent_password),
        role="agent",
    )
    carlos = Agent(
        name="Carlos Vega",
        email="carlos@veranda.gt",
        hashed_password=hash_password(agent_password),
        role="agent",
    )
    sofia = Agent(
        name="Sofía Directora",
        email="admin@estatehub.gt",
        hashed_password=hash_password(admin_password),
        role="admin",
    )
    session.add_all([ana, carlos, sofia])
    session.commit()
    session.refresh(ana)
    session.refresh(carlos)
    assert ana.id is not None and carlos.id is not None

    session.add_all(
        [
            Property(
                owner_agent_id=ana.id,
                title="Penthouse Vista Volcán de Agua",
                city="Antigua Guatemala",
                price=395_000,
                bedrooms=3,
            ),
            Property(
                owner_agent_id=ana.id,
                title="Loft Botánico Zona 14",
                city="Ciudad de Guatemala",
                price=245_000,
                bedrooms=2,
            ),
            Property(
                owner_agent_id=carlos.id,
                title="Villa Jardín Las Luces",
                city="Santa Catarina Pinula",
                price=480_000,
                bedrooms=4,
                status="reserved",
            ),
        ]
    )
    session.commit()
    logger.info("Datos de demostración sembrados (3 agentes, 3 inmuebles).")
    return True
