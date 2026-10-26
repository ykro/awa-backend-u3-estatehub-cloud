from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

PitchSource = Literal["gemini", "deterministic-fallback"]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class AgentPublic(BaseModel):
    """DTO de salida para usuarios autenticados: nunca incluye hashed_password."""

    id: int
    name: str
    email: str
    role: str


class TokenRequest(BaseModel):
    """Entrada del login. El correo se normaliza en el servidor con normalize_email()."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in_minutes: int
    agent: AgentPublic


class PropertyCreate(BaseModel):
    """El dueño nunca viaja en el body: sale del token. extra=forbid evita mass assignment."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=4, max_length=120)
    city: str = Field(min_length=2, max_length=60)
    price: int = Field(gt=0, le=50_000_000)
    bedrooms: int = Field(ge=1, le=20)

    @field_validator("title", "city")
    @classmethod
    def collapse_whitespace(cls, value: str, info: ValidationInfo) -> str:
        # El mínimo se vuelve a medir después de colapsar espacios: "  ab  " no es un título.
        cleaned = " ".join(value.split())
        minimum = 4 if info.field_name == "title" else 2
        if len(cleaned) < minimum:
            raise ValueError(f"Debe tener al menos {minimum} caracteres sin contar espacios.")
        return cleaned


class PropertyStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "reserved", "sold"]


class PropertyResponse(BaseModel):
    """DTO público del catálogo: expone el nombre del agente, no su correo."""

    id: int
    owner_agent_id: int
    owner_agent_name: str
    title: str
    city: str
    price: int
    bedrooms: int
    status: str
    ai_pitch: str | None = None


class PropertyPitchResponse(BaseModel):
    property_id: int
    headline: str
    highlights: list[str]
    target_buyer: str
    source: PitchSource
