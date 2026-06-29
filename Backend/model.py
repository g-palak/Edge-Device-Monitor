from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum
from database import Base
import enum
from datetime import datetime

class ConfigStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"

class Telemetry(Base):
    __tablename__ = "telemetry"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    ts = Column(DateTime, default=datetime.utcnow)
    metric = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class DeviceConfig(Base):
    __tablename__ = "device_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    config_data = Column(String)  # JSON string
    status = Column(SQLEnum(ConfigStatus), default=ConfigStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)