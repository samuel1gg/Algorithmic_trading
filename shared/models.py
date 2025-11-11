"""Shared data models across services."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from enum import Enum


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class MarketData(BaseModel):
    """Market data point from data ingestion."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TradingSignal(BaseModel):
    """Trading signal from ML service."""
    symbol: str
    timestamp: datetime
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0)
    predicted_price: Optional[float] = None
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    model_version: str = "v1.0"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnomalyAlert(BaseModel):
    """Anomaly detection alert."""
    symbol: str
    timestamp: datetime
    anomaly_score: float
    anomaly_type: str
    description: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    market_data: MarketData
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Order(BaseModel):
    """Trading order."""
    order_id: Optional[str] = None
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None  # For limit orders
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Position(BaseModel):
    """Portfolio position."""
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Portfolio(BaseModel):
    """Portfolio snapshot."""
    total_value: float
    cash: float
    positions: list[Position]
    total_pnl: float
    total_return: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BacktestResult(BaseModel):
    """Backtesting results."""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_win: float
    average_loss: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

