from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class TelemetryCreate(BaseModel):
    device_id: str
    ts: datetime
    metric: float

class TelemetryResponse(BaseModel):
    id: int
    device_id: str
    ts: datetime
    metric: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class ConfigCreate(BaseModel):
    config_data: Dict[str, Any]

class ConfigResponse(BaseModel):
    id: int
    device_id: str
    config_data: str
    status: str
    created_at: datetime
    applied_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ConfigAck(BaseModel):
    config_id: int
    status: str