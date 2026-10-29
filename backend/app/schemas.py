from datetime import date, datetime, timezone, timedelta
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict

class Strict(BaseModel): model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
class RouteRequest(Strict):
    origin: str = Field(min_length=3, max_length=200)
    destination: str = Field(min_length=3, max_length=200)
    corridor_m: int = Field(default=300, ge=50, le=1000)
    @field_validator('origin', 'destination')
    @classmethod
    def location(cls, v):
        if len(v.strip()) < 3: raise ValueError('Enter a location or latitude,longitude')
        return v.strip()
class AnalysisRequest(Strict):
    route_id: UUID
    start_date: date
    end_date: date
    fallback_days: int = Field(default=90, ge=0, le=365)
    @model_validator(mode='after')
    def dates(self):
        if not self.start_date < self.end_date or (self.end_date-self.start_date).days > 180:
            raise ValueError('Date interval must be between 1 and 180 days; end is exclusive')
        if self.end_date > datetime.now(timezone.utc).date()+timedelta(days=1): raise ValueError('Future imagery unavailable')
        return self
class IncidentRequest(Strict):
    client_id: UUID
    kind: Literal['LANDSLIDE','BLOCKAGE','DEBRIS','OTHER']
    latitude: float = Field(ge=24, le=30)
    longitude: float = Field(ge=88, le=98)
    observed_at: datetime
    description: str = Field(min_length=10, max_length=3000)
    direction: str | None = Field(default=None, max_length=100)
    route_id: UUID | None = None
    segment_id: UUID | None = None
    @field_validator('observed_at')
    @classmethod
    def observed(cls,v):
        if v.tzinfo is None: raise ValueError('Include a timezone')
        if v > datetime.now(timezone.utc)+timedelta(minutes=5): raise ValueError('Observation cannot be in future')
        return v.astimezone(timezone.utc)
class Verification(Strict):
    decision: Literal['VERIFIED','REJECTED']
    notes: str = Field(min_length=10,max_length=3000)
    source: str = Field(min_length=5,max_length=500)
    observed_at: datetime
    closure: bool = False
    expires_at: datetime
    @model_validator(mode='after')
    def validate_times(self):
        if self.observed_at.tzinfo is None or self.expires_at.tzinfo is None: raise ValueError('Include timezones')
        if self.observed_at > datetime.now(timezone.utc)+timedelta(minutes=5): raise ValueError('Future evidence')
        if self.expires_at <= self.observed_at or self.expires_at-self.observed_at > timedelta(days=7): raise ValueError('Evidence validity must be 0–7 days')
        if self.closure and self.decision != 'VERIFIED': raise ValueError('Rejected evidence cannot confirm closure')
        return self
class IncidentStatus(Strict):
    status: Literal['ACTIVE','RESOLVED']
    notes: str = Field(min_length=10,max_length=3000)
class Login(Strict):
    username: str = Field(min_length=1,max_length=80)
    password: str = Field(min_length=1,max_length=200)
