from __future__ import annotations

from sqlmodel import Session, select

from app.config import settings
from app.models import Agent, Property
from app.pitch import generate_pitch_draft
from app.schemas import (
    AgentPublic,
    PropertyCreate,
    PropertyPitchResponse,
    PropertyResponse,
    PropertyStatusUpdate,
    TokenRequest,
    TokenResponse,
)
from app.security import (
    AuthenticationError,
    ForbiddenOwnerError,
    create_access_token,
    decoy_password_hash,
    normalize_email,
    verify_password,
)

INVALID_CREDENTIALS_MESSAGE = "Correo o contraseña incorrectos."


class PropertyNotFoundError(Exception):
    def __init__(self, property_id: int) -> None:
        super().__init__(f"El inmueble #{property_id} no existe.")
        self.property_id = property_id


def to_agent_public(agent: Agent) -> AgentPublic:
    assert agent.id is not None
    return AgentPublic(id=agent.id, name=agent.name, email=agent.email, role=agent.role)


class EstateCloudRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- Agentes y autenticación -------------------------------------------------

    def list_agents(self) -> list[AgentPublic]:
        agents = self.session.exec(select(Agent).order_by(Agent.id)).all()
        return [to_agent_public(a) for a in agents]

    def get_agent_by_id(self, agent_id: int) -> Agent | None:
        return self.session.get(Agent, agent_id)

    def authenticate_and_issue_token(self, credentials: TokenRequest) -> TokenResponse:
        """TODO (taller, paso 3): login sin enumeración de cuentas.

        1. Normaliza el correo con normalize_email y busca al agente.
        2. Si no existe, verifica la contraseña contra decoy_password_hash() (mismo costo)
           y lanza AuthenticationError(INVALID_CREDENTIALS_MESSAGE, code="INVALID_CREDENTIALS").
        3. Si la contraseña no coincide, lanza exactamente el mismo error.
        4. Si coincide, firma el token y devuelve TokenResponse con to_agent_public(agent).
        """
        _ = (credentials, normalize_email, verify_password, decoy_password_hash)
        _ = (AuthenticationError, create_access_token, settings)
        raise NotImplementedError("Taller, paso 3: implementa authenticate_and_issue_token")

    # ----- Inmuebles ------------------------------------------------------------------

    def _to_property_response(self, prop: Property, owner: Agent) -> PropertyResponse:
        assert prop.id is not None and owner.id is not None
        return PropertyResponse(
            id=prop.id,
            owner_agent_id=owner.id,
            owner_agent_name=owner.name,
            title=prop.title,
            city=prop.city,
            price=prop.price,
            bedrooms=prop.bedrooms,
            status=prop.status,
            ai_pitch=prop.ai_pitch,
        )

    def _owner_of(self, prop: Property) -> Agent:
        owner = self.session.get(Agent, prop.owner_agent_id)
        assert owner is not None
        return owner

    def _get_owned_property_or_raise(self, property_id: int, current_agent: Agent) -> Property:
        """TODO (taller, paso 5): guarda anti-IDOR (BOLA) que usan PATCH, DELETE y pitch.

        404 (PropertyNotFoundError) si el inmueble no existe; 403 (ForbiddenOwnerError) si
        current_agent no es el dueño y su rol no es "admin". Devuelve el inmueble.
        """
        _ = (property_id, current_agent, ForbiddenOwnerError)
        raise NotImplementedError("Taller, paso 5: implementa la guarda de dueño")

    def list_properties(self) -> list[PropertyResponse]:
        statement = (
            select(Property, Agent)
            .join(Agent, Property.owner_agent_id == Agent.id)  # type: ignore[arg-type]
            .order_by(Property.id)  # type: ignore[arg-type]
        )
        return [self._to_property_response(p, a) for p, a in self.session.exec(statement).all()]

    def create_property(self, payload: PropertyCreate, current_agent: Agent) -> PropertyResponse:
        assert current_agent.id is not None
        prop = Property(owner_agent_id=current_agent.id, **payload.model_dump())
        self.session.add(prop)
        self.session.commit()
        self.session.refresh(prop)
        return self._to_property_response(prop, current_agent)

    def update_property_status(
        self,
        property_id: int,
        payload: PropertyStatusUpdate,
        current_agent: Agent,
    ) -> PropertyResponse:
        prop = self._get_owned_property_or_raise(property_id, current_agent)
        prop.status = payload.status
        self.session.add(prop)
        self.session.commit()
        self.session.refresh(prop)
        return self._to_property_response(prop, self._owner_of(prop))

    def delete_property(self, property_id: int, current_agent: Agent) -> None:
        prop = self._get_owned_property_or_raise(property_id, current_agent)
        self.session.delete(prop)
        self.session.commit()

    def generate_property_pitch(
        self, property_id: int, current_agent: Agent
    ) -> PropertyPitchResponse:
        prop = self._get_owned_property_or_raise(property_id, current_agent)
        draft, source = generate_pitch_draft(prop)
        prop.ai_pitch = draft.headline
        self.session.add(prop)
        self.session.commit()
        return PropertyPitchResponse(
            property_id=property_id,
            headline=draft.headline,
            highlights=draft.highlights,
            target_buyer=draft.target_buyer,
            source=source,
        )
