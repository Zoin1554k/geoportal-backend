import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------- Auth ----------
class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    role: str
    created_at: datetime


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str
    user: UserOut


class RefreshIn(BaseModel):
    refreshToken: str


# ---------- Layers ----------
class LayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    type: Literal["geojson", "wms", "xyz"]
    source_url: str | None = None
    style: dict[str, Any] = Field(default_factory=dict)
    is_public: bool = False


class LayerUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    style: dict[str, Any] | None = None
    is_public: bool | None = None


class LayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None
    type: str
    source_url: str | None
    style: dict[str, Any]
    feature_count: int
    owner_id: uuid.UUID | None
    is_public: bool
    created_at: datetime
    updated_at: datetime


# ---------- Features ----------
class BBoxQuery(BaseModel):
    bbox: str
    limit: int | None = None
    simplify: float = 0.0

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: str) -> str:
        parts = v.split(",")
        if len(parts) != 4:
            raise ValueError("bbox deve ter 4 valores: oeste,sul,leste,norte")
        try:
            [float(p) for p in parts]
        except ValueError:
            raise ValueError("bbox contém valores não numéricos")
        return v