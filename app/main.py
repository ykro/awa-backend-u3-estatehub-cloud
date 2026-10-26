from __future__ import annotations

import logging
import secrets
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Path, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import engine, get_session, init_db, seed_demo_data
from app.models import Agent
from app.repository import EstateCloudRepository, PropertyNotFoundError, to_agent_public
from app.schemas import (
    AgentPublic,
    ErrorDetail,
    ErrorEnvelope,
    PropertyCreate,
    PropertyPitchResponse,
    PropertyResponse,
    PropertyStatusUpdate,
    TokenRequest,
    TokenResponse,
)
from app.security import AuthenticationError, ForbiddenOwnerError, decode_access_token
from app.ui import render_console_html
from app.validation_es import validation_details

logging.basicConfig(level=logging.WARNING)
logging.getLogger("estatehub").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    init_db()
    with Session(engine) as session:
        seed_demo_data(session)
    yield


app = FastAPI(
    title=settings.app_name,
    version="3.0.0",
    description=(
        "API inmobiliaria con autenticación JWT, autorización por propietario (anti-IDOR), "
        "protección contra fuerza bruta en el login y despliegue en Cloud Run."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


bearer_scheme = HTTPBearer(auto_error=False)

# Ids acotados al rango de un entero de 32 bits: un id gigante responde 422, nunca 500.
MAX_ID = 2_147_483_647
PropertyId = Annotated[int, Path(ge=1, le=MAX_ID, description="Id del inmueble")]


class AdminOnlyError(Exception):
    """Identidad válida sin rol admin: se traduce a HTTP 403."""


def get_repository(session: Annotated[Session, Depends(get_session)]) -> EstateCloudRepository:
    return EstateCloudRepository(session)


RepoDep = Annotated[EstateCloudRepository, Depends(get_repository)]


def get_current_agent(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    repo: RepoDep,
) -> Agent:
    """TODO (taller, paso 4): barrera de identidad. Cualquier falla es 401.

    1. Si credentials es None, lanza AuthenticationError (falta el encabezado).
    2. Decodifica con decode_access_token(credentials.credentials).
    3. El claim sub debe ser un id en texto con solo dígitos ASCII (isascii e isdigit) y
       no mayor que MAX_ID; si no, AuthenticationError (nunca un 500).
    4. Carga el agente con repo.get_agent_by_id; si ya no existe, AuthenticationError.
    """
    _ = (credentials, repo, decode_access_token)
    raise NotImplementedError("Taller, paso 4: implementa get_current_agent")


CurrentAgentDep = Annotated[Agent, Depends(get_current_agent)]


def _error(status_code: int, code: str, message: str, **details: object) -> JSONResponse:
    envelope = ErrorEnvelope(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=jsonable_encoder(envelope))


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(_: Request, exc: AuthenticationError) -> JSONResponse:
    response = _error(status.HTTP_401_UNAUTHORIZED, exc.code, exc.message)
    response.headers["WWW-Authenticate"] = "Bearer"
    return response


@app.exception_handler(ForbiddenOwnerError)
async def forbidden_owner_handler(_: Request, exc: ForbiddenOwnerError) -> JSONResponse:
    return _error(
        status.HTTP_403_FORBIDDEN, "FORBIDDEN_NOT_OWNER", str(exc), property_id=exc.property_id
    )


@app.exception_handler(PropertyNotFoundError)
async def property_not_found_handler(_: Request, exc: PropertyNotFoundError) -> JSONResponse:
    return _error(
        status.HTTP_404_NOT_FOUND, "PROPERTY_NOT_FOUND", str(exc), property_id=exc.property_id
    )


@app.exception_handler(AdminOnlyError)
async def admin_only_handler(_: Request, __: AdminOnlyError) -> JSONResponse:
    return _error(
        status.HTTP_403_FORBIDDEN,
        "FORBIDDEN_ADMIN_ONLY",
        "Solo un admin puede ver esta información.",
    )


# Errores que genera Starlette sin pasar por la app (ruta inexistente, método no permitido,
# cuerpo que no es UTF-8): en español y dentro del mismo sobre {"error": {...}}.
_HTTP_ERRORS = {
    404: ("NOT_FOUND", "La ruta solicitada no existe."),
    405: ("METHOD_NOT_ALLOWED", "Método HTTP no permitido en esta ruta."),
}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 400:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "VALIDATION_ERROR",
            "Los datos enviados no cumplen el contrato.",
            errors=[
                {"loc": ["body"], "msg": "El cuerpo no es JSON válido", "type": "json_invalid"}
            ],
        )
    code, message = _HTTP_ERRORS.get(exc.status_code, ("HTTP_ERROR", "Error HTTP."))
    response = _error(exc.status_code, code, message)
    for name, value in (exc.headers or {}).items():
        response.headers[name] = value
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Solo loc, msg y type: 'input' repetiría la contraseña y 'ctx' puede traer objetos
    # no serializables (un ValueError) que convertirían el 422 en un 500.
    errors = validation_details(exc.errors())
    return _error(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "VALIDATION_ERROR",
        "Los datos enviados no cumplen el contrato.",
        errors=errors,
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root_console() -> HTMLResponse:
    nonce = secrets.token_urlsafe(16)
    csp = (
        "default-src 'none'; "
        f"script-src 'nonce-{nonce}'; "
        f"style-src 'nonce-{nonce}'; "
        "connect-src 'self'; img-src 'self' data:; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    return HTMLResponse(
        content=render_console_html(nonce),
        headers={"Content-Security-Policy": csp, "Cache-Control": "no-store"},
    )


@app.get("/health", summary="Sonda de salud")
def health_check() -> dict[str, str | None]:
    # owner identifica el repositorio y commit el SHA desplegado (null si no se inyectó).
    return {
        "status": "ok",
        "service": settings.service_name,
        "owner": settings.owner,
        "commit": settings.commit_sha,
    }


@app.get("/api/v1/agents", response_model=list[AgentPublic], summary="Listar agentes (solo admin)")
def list_agents(current_agent: CurrentAgentDep, repo: RepoDep) -> list[AgentPublic]:
    # Correos y roles de todo el personal: solo para admin (mínimo privilegio).
    if current_agent.role != "admin":
        raise AdminOnlyError()
    return repo.list_agents()


@app.post(
    "/api/v1/auth/token",
    response_model=TokenResponse,
    summary="Iniciar sesión y obtener un token",
    responses={401: {"model": ErrorEnvelope}},
)
def login_for_access_token(payload: TokenRequest, repo: RepoDep) -> TokenResponse:
    # TODO (reto autónomo): protección contra fuerza bruta. Lee la especificación completa
    # en README.md. Usa las dependencias get_login_guard y get_clock de app/login_guard.py
    # (los tests las reemplazan) y responde 429 con Retry-After y TOO_MANY_ATTEMPTS.
    return repo.authenticate_and_issue_token(payload)


@app.get("/api/v1/auth/me", response_model=AgentPublic, summary="Agente de la sesión")
def read_current_agent(current_agent: CurrentAgentDep) -> AgentPublic:
    return to_agent_public(current_agent)


@app.get("/api/v1/properties", response_model=list[PropertyResponse], summary="Catálogo público")
def list_properties(repo: RepoDep) -> list[PropertyResponse]:
    return repo.list_properties()


@app.post(
    "/api/v1/properties",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publicar inmueble",
)
def create_property(
    payload: PropertyCreate, current_agent: CurrentAgentDep, repo: RepoDep
) -> PropertyResponse:
    return repo.create_property(payload, current_agent)


@app.patch(
    "/api/v1/properties/{property_id}/status",
    response_model=PropertyResponse,
    summary="Cambiar estado (dueño o admin)",
)
def update_property_status(
    property_id: PropertyId,
    payload: PropertyStatusUpdate,
    current_agent: CurrentAgentDep,
    repo: RepoDep,
) -> PropertyResponse:
    return repo.update_property_status(property_id, payload, current_agent)


@app.delete(
    "/api/v1/properties/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Borrar inmueble (dueño o admin)",
)
def delete_property(
    property_id: PropertyId, current_agent: CurrentAgentDep, repo: RepoDep
) -> Response:
    repo.delete_property(property_id, current_agent)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/api/v1/properties/{property_id}/generate-pitch",
    response_model=PropertyPitchResponse,
    summary="Generar pitch comercial (dueño o admin)",
)
def generate_property_pitch(
    property_id: PropertyId, current_agent: CurrentAgentDep, repo: RepoDep
) -> PropertyPitchResponse:
    return repo.generate_property_pitch(property_id, current_agent)
