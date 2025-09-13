from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Base response schema
class BaseResponse(BaseModel):
    ok: bool
    data: Optional[dict] = None
    error: Optional[str] = None

# Load schemas
class LoadBase(BaseModel):
    load_id: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    pickup_date: datetime
    delivery_date: datetime
    equipment_type: str
    weight: float
    miles: float
    rate_per_mile: float
    total_rate: float
    commodity: Optional[str] = None
    special_requirements: Optional[str] = None
    broker_name: Optional[str] = None
    broker_mc: Optional[str] = None

class LoadCreate(LoadBase):
    pass

class Load(LoadBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class LoadSearchRequest(BaseModel):
    # Required origin location
    origin_city: str = Field(..., description="Required origin city")
    origin_state: str = Field(..., description="Required origin state")
    
    # Optional destination preferences
    destination_city: Optional[str] = None
    destination_state: Optional[str] = None
    
    # Equipment and rate filters
    equipment_type: Optional[str] = None
    min_rate: Optional[float] = None
    max_rate: Optional[float] = None
    limit: int = Field(default=10, le=100)
    
    # Flexibility settings
    flexible_origin: bool = Field(default=False, description="Allow nearby origin cities")
    flexible_destination: bool = Field(default=False, description="Allow nearby destination cities")

class LoadSearchResponse(BaseResponse):
    data: Optional[dict] = Field(None, description="Contains 'loads' list and 'total' count")

# FMCSA schemas
class FMCSAVerifyRequest(BaseModel):
    mc_number: str = Field(..., description="Motor Carrier number to verify")

class FMCSAVerifyResponse(BaseResponse):
    data: Optional[dict] = Field(None, description="Contains FMCSA verification details")

# Negotiation schemas
class NegotiationRequest(BaseModel):
    load_id: str
    carrier_mc: str
    current_rate: float
    negotiation_round: int = 1

class NegotiationResponse(BaseResponse):
    data: Optional[dict] = Field(None, description="Contains negotiation result and counter offer")

# Call schemas
class CallBase(BaseModel):
    call_id: str
    load_id: str
    carrier_mc: str
    carrier_name: Optional[str] = None
    initial_rate: float
    current_rate: float
    negotiation_round: int = 1
    max_rounds: int = 3
    status: str
    call_duration_seconds: Optional[int] = None
    notes: Optional[str] = None

class CallCreate(CallBase):
    pass

class Call(CallBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CallPersistRequest(BaseModel):
    call_id: str
    load_id: str
    carrier_mc: str
    carrier_name: Optional[str] = None
    initial_rate: float
    current_rate: float
    negotiation_round: int = 1
    status: str
    call_duration_seconds: Optional[int] = None
    notes: Optional[str] = None

class CallPersistResponse(BaseResponse):
    data: Optional[dict] = Field(None, description="Contains persisted call details")

# Metrics schemas
class MetricsSummaryResponse(BaseResponse):
    data: Optional[dict] = Field(None, description="Contains KPI metrics summary")

class MetricsDetail(BaseModel):
    total_calls: int
    successful_calls: int
    average_call_duration: float
    average_negotiation_rounds: float
    acceptance_rate: float
    total_revenue: float
    average_rate_per_mile: float
