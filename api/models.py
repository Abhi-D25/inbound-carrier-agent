from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.db import Base

class Load(Base):
    __tablename__ = "loads"
    
    id = Column(Integer, primary_key=True, index=True)
    load_id = Column(String, unique=True, index=True, nullable=False)
    origin_city = Column(String, nullable=False)
    origin_state = Column(String, nullable=False)
    destination_city = Column(String, nullable=False)
    destination_state = Column(String, nullable=False)
    pickup_date = Column(DateTime, nullable=False)
    delivery_date = Column(DateTime, nullable=False)
    equipment_type = Column(String, nullable=False)  # e.g., "Dry Van", "Refrigerated"
    weight = Column(Float, nullable=False)
    miles = Column(Float, nullable=False)
    rate_per_mile = Column(Float, nullable=False)
    total_rate = Column(Float, nullable=False)
    commodity = Column(String, nullable=True)
    special_requirements = Column(Text, nullable=True)
    broker_name = Column(String, nullable=True)
    broker_mc = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship to calls
    calls = relationship("Call", back_populates="load")

class Call(Base):
    __tablename__ = "calls"
    
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String, unique=True, index=True, nullable=False)
    load_id = Column(String, ForeignKey("loads.load_id"), nullable=True)
    carrier_mc = Column(String, nullable=False)
    carrier_name = Column(String, nullable=True)
    fmcsa_status = Column(String, nullable=True)  # FMCSA verification status
    initial_rate = Column(Float, nullable=True)
    current_rate = Column(Float, nullable=True)
    listed_rate = Column(Float, nullable=True)
    final_rate = Column(Float, nullable=True)
    last_offer = Column(Float, nullable=True)
    negotiation_rounds = Column(Integer, default=0)
    outcome = Column(String, nullable=False)  # "accepted", "rejected", "no_agreement", "expired"
    sentiment = Column(String, nullable=True)  # "positive", "neutral", "negative"
    extracted_json = Column(Text, nullable=True)  # JSON string of extracted data
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    call_duration_seconds = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship to load
    load = relationship("Load", back_populates="calls")
