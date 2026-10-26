from sqlmodel import Field, Relationship, SQLModel


class Agent(SQLModel, table=True):
    __tablename__ = "agents"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=2, max_length=80)
    email: str = Field(unique=True, index=True, min_length=5, max_length=120)
    hashed_password: str = Field(min_length=20)
    role: str = Field(default="agent", max_length=20)

    properties: list["Property"] = Relationship(back_populates="owner_agent")


class Property(SQLModel, table=True):
    __tablename__ = "properties"

    id: int | None = Field(default=None, primary_key=True)
    owner_agent_id: int = Field(foreign_key="agents.id", index=True)
    title: str = Field(min_length=4, max_length=120)
    city: str = Field(index=True, min_length=2, max_length=60)
    price: int = Field(gt=0, le=50_000_000)
    bedrooms: int = Field(ge=1, le=20)
    status: str = Field(default="available", max_length=20)
    ai_pitch: str | None = Field(default=None, max_length=600)

    owner_agent: Agent | None = Relationship(back_populates="properties")
