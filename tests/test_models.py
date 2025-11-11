"""Basic tests for shared models."""
import pytest
from datetime import datetime
from shared.models import MarketData, TradingSignal, Order, OrderSide, OrderType, OrderStatus


def test_market_data():
    """Test MarketData model."""
    data = MarketData(
        symbol="AAPL",
        timestamp=datetime.utcnow(),
        open=150.0,
        high=152.0,
        low=149.0,
        close=151.0,
        volume=1000000
    )
    assert data.symbol == "AAPL"
    assert data.close == 151.0


def test_trading_signal():
    """Test TradingSignal model."""
    signal = TradingSignal(
        symbol="AAPL",
        timestamp=datetime.utcnow(),
        action="BUY",
        confidence=0.8,
        current_price=150.0,
        predicted_price=155.0
    )
    assert signal.action == "BUY"
    assert signal.confidence == 0.8


def test_order():
    """Test Order model."""
    order = Order(
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10.0,
        status=OrderStatus.PENDING
    )
    assert order.side == OrderSide.BUY
    assert order.quantity == 10.0

