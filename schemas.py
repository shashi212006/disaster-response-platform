import datetime as dt
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Category = Literal["flood", "fire", "earthquake", "cyclone", "medical", "landslide", "other"]

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=100)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class RoleIn(BaseModel):
    role: Literal["citizen", "responder", "admin"]

class IncidentIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=2000)
    category: Category
    location: str = Field(min_length=2, max_length=120)
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)

class IncidentOut(IncidentIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    severity: int
    status: str
    ai_summary: str
    ai_actions: str
    created_at: dt.datetime

class StatusIn(BaseModel):
    status: Literal["reported", "verified", "responding", "resolved"]

class ResourceIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    type: str = Field(min_length=2, max_length=30)
    quantity: int = Field(ge=0)
    location: str = Field(min_length=2, max_length=120)

class ResourceOut(ResourceIn):
    model_config = ConfigDict(from_attributes=True)
    id: int

class DispatchIn(BaseModel):
    resource_id: int
    quantity: int = Field(gt=0)
