"""SQLAlchemy database models."""
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean, 
    ForeignKey, Index, CheckConstraint, Text, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from shared.database import Base


class MarketDataPoint(Base):
    """Time-series market data storage."""
    __tablename__ = "market_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    vwap = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_market_data_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_market_data_timestamp', 'timestamp'),
    )


class TradingSignal(Base):
    """Trading signals from ML service."""
    __tablename__ = "trading_signals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    action = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, nullable=False)
    predicted_price = Column(Float, nullable=True)
    current_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    model_version = Column(String(20), nullable=False)
    executed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Anomaly(Base):
    """Anomaly detection alerts."""
    __tablename__ = "anomalies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False)
    anomaly_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    """Trading orders."""
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(String(50), unique=True, nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY, SELL
    order_type = Column(String(10), nullable=False)  # MARKET, LIMIT, STOP
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # For limit orders
    status = Column(String(20), nullable=False, default="PENDING")
    filled_quantity = Column(Float, default=0.0)
    average_fill_price = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_positive_quantity'),
        CheckConstraint('filled_quantity <= quantity', name='check_filled_quantity'),
    )


class Position(Base):
    """Portfolio positions."""
    __tablename__ = "positions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Trade(Base):
    """Executed trades."""
    __tablename__ = "trades"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    pnl = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Portfolio(Base):
    """Portfolio snapshots."""
    __tablename__ = "portfolio_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    total_value = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)
    total_pnl = Column(Float, default=0.0)
    total_return = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Account(Base):
    """Trading account."""
    __tablename__ = "account"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cash = Column(Float, nullable=False, default=100000.0)
    total_value = Column(Float, nullable=False, default=100000.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint('cash >= 0', name='check_non_negative_cash'),
    )

