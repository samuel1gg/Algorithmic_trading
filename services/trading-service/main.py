"""Trading Service - Order execution, portfolio management, and risk management."""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session
import uuid
from shared.config import settings
from shared.logger import setup_logger
from shared.kafka_client import KafkaConsumerClient, KafkaProducerClient
from shared.database import get_db_session, get_db
from shared.models import Order as OrderModel, Position as PositionModel, Portfolio as PortfolioModel
from database.models import (
    Order, Position, Trade, Account, MarketDataPoint
)
import threading
import time

logger = setup_logger(__name__)

# Global clients
kafka_producer = None
kafka_consumer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global kafka_producer, kafka_consumer
    
    # Initialize Kafka
    kafka_producer = KafkaProducerClient()
    kafka_consumer = KafkaConsumerClient(
        topics=[settings.kafka_topic_trading_signals],
        group_id="trading-service"
    )
    
    # Start background order processing
    background_thread = threading.Thread(target=process_trading_signals, daemon=True)
    background_thread.start()
    
    # Start position update thread
    update_thread = threading.Thread(target=update_positions_prices, daemon=True)
    update_thread.start()
    
    logger.info("Trading service started")
    yield
    
    if kafka_consumer:
        kafka_consumer.close()
    if kafka_producer:
        kafka_producer.close()
    logger.info("Trading service stopped")


app = FastAPI(
    title="Trading Service",
    description="Trading service for order execution and portfolio management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)


def check_risk_limits(symbol: str, side: str, quantity: float, price: float, db: Session) -> tuple[bool, str]:
    """Check risk management limits before executing order."""
    try:
        # Get account
        account = db.query(Account).first()
        if not account:
            return False, "Account not found"
        
        # Get current positions
        position = db.query(Position).filter(Position.symbol == symbol).first()
        
        if side == "BUY":
            # Check available cash
            required_cash = quantity * price
            if account.cash < required_cash:
                return False, f"Insufficient cash. Required: ${required_cash:.2f}, Available: ${account.cash:.2f}"
            
            # Check position size limit
            portfolio_value = account.total_value
            position_value = quantity * price
            if position_value > portfolio_value * settings.max_position_size:
                return False, f"Position size exceeds limit. Max: {settings.max_position_size*100}% of portfolio"
            
            # Check if adding to position would exceed limit
            if position:
                new_position_value = (position.quantity + quantity) * price
                if new_position_value > portfolio_value * settings.max_position_size:
                    return False, "Adding to position would exceed size limit"
        
        elif side == "SELL":
            # Check if we have the position
            if not position or position.quantity < quantity:
                return False, f"Insufficient position. Available: {position.quantity if position else 0}, Requested: {quantity}"
        
        return True, "OK"
    except Exception as e:
        logger.error(f"Error checking risk limits: {e}")
        return False, str(e)


def execute_order(order: Order, db: Session) -> bool:
    """Execute an order."""
    try:
        # Get current market price
        market_data = db.query(MarketDataPoint).filter(
            MarketDataPoint.symbol == order.symbol
        ).order_by(MarketDataPoint.timestamp.desc()).first()
        
        if not market_data:
            logger.error(f"No market data for {order.symbol}")
            return False
        
        execution_price = market_data.close
        
        # For limit orders, check if price is acceptable
        if order.order_type == "LIMIT":
            if order.side == "BUY" and execution_price > order.price:
                logger.info(f"Limit order not executed. Market price {execution_price} > limit {order.price}")
                return False
            elif order.side == "SELL" and execution_price < order.price:
                logger.info(f"Limit order not executed. Market price {execution_price} < limit {order.price}")
                return False
        
        # Execute the order
        order.status = "FILLED"
        order.filled_quantity = order.quantity
        order.average_fill_price = execution_price
        order.filled_at = datetime.utcnow()
        db.commit()
        
        # Create trade record
        trade = Trade(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=execution_price,
            commission=order.quantity * execution_price * 0.001,  # 0.1% commission
            timestamp=datetime.utcnow()
        )
        db.add(trade)
        
        # Update position
        position = db.query(Position).filter(Position.symbol == order.symbol).first()
        
        if order.side == "BUY":
            if position:
                # Update existing position
                total_cost = (position.quantity * position.average_price) + (order.quantity * execution_price)
                total_quantity = position.quantity + order.quantity
                position.average_price = total_cost / total_quantity
                position.quantity = total_quantity
                position.current_price = execution_price
            else:
                # Create new position
                position = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    average_price=execution_price,
                    current_price=execution_price,
                    unrealized_pnl=0.0
                )
                db.add(position)
        else:  # SELL
            if position:
                # Calculate realized PnL
                realized_pnl = (execution_price - position.average_price) * order.quantity
                position.realized_pnl += realized_pnl
                position.quantity -= order.quantity
                position.current_price = execution_price
                
                # Remove position if fully closed
                if position.quantity <= 0:
                    db.delete(position)
        
        # Update account cash
        account = db.query(Account).first()
        if order.side == "BUY":
            account.cash -= (order.quantity * execution_price + trade.commission)
        else:  # SELL
            account.cash += (order.quantity * execution_price - trade.commission)
        
        db.commit()
        
        # Update portfolio value using stored procedure
        db.execute(text("SELECT update_portfolio_value()"))
        db.commit()
        
        logger.info(f"Order {order.order_id} executed: {order.side} {order.quantity} {order.symbol} @ ${execution_price:.2f}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error executing order: {e}")
        return False


def process_trading_signals():
    """Process trading signals from Kafka."""
    def process_signal(signal_data: dict, key: Optional[str]):
        try:
            from shared.models import TradingSignal
            signal = TradingSignal(**signal_data)
            
            if signal.action == "HOLD":
                return
            
            db = get_db_session()
            try:
                # Check risk limits
                quantity = calculate_order_quantity(signal, db)
                if quantity <= 0:
                    logger.info(f"Order quantity too small for {signal.symbol}")
                    return
                
                # Use current price for market orders
                market_data = db.query(MarketDataPoint).filter(
                    MarketDataPoint.symbol == signal.symbol
                ).order_by(MarketDataPoint.timestamp.desc()).first()
                
                if not market_data:
                    logger.error(f"No market data for {signal.symbol}")
                    return
                
                price = market_data.close
                
                # Check risk limits
                can_execute, reason = check_risk_limits(
                    signal.symbol, signal.action, quantity, price, db
                )
                
                if not can_execute:
                    logger.warning(f"Order rejected for {signal.symbol}: {reason}")
                    return
                
                # Create order
                order = Order(
                    order_id=str(uuid.uuid4()),
                    symbol=signal.symbol,
                    side=signal.action,
                    order_type="MARKET",
                    quantity=quantity,
                    price=None,
                    status="PENDING",
                    timestamp=datetime.utcnow()
                )
                db.add(order)
                db.commit()
                
                # Execute order
                if execute_order(order, db):
                    logger.info(f"Order executed from signal: {signal.action} {quantity} {signal.symbol}")
                else:
                    order.status = "REJECTED"
                    db.commit()
                    
            except Exception as e:
                db.rollback()
                logger.error(f"Error processing signal: {e}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in signal processing: {e}")
    
    while True:
        try:
            kafka_consumer.consume(process_signal)
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
            time.sleep(5)


def calculate_order_quantity(signal, db: Session) -> float:
    """Calculate order quantity based on signal and risk limits."""
    try:
        account = db.query(Account).first()
        if not account:
            return 0.0
        
        # Use a percentage of portfolio for position sizing
        portfolio_value = account.total_value
        position_value = portfolio_value * settings.max_position_size * signal.confidence
        
        # Get current price
        market_data = db.query(MarketDataPoint).filter(
            MarketDataPoint.symbol == signal.symbol
        ).order_by(MarketDataPoint.timestamp.desc()).first()
        
        if not market_data:
            return 0.0
        
        price = market_data.close
        quantity = position_value / price
        
        # Round to reasonable precision
        return round(quantity, 2)
    except Exception as e:
        logger.error(f"Error calculating order quantity: {e}")
        return 0.0


def update_positions_prices():
    """Periodically update position prices and PnL."""
    while True:
        try:
            time.sleep(60)  # Update every minute
            db = get_db_session()
            try:
                positions = db.query(Position).all()
                for position in positions:
                    # Get latest market price
                    market_data = db.query(MarketDataPoint).filter(
                        MarketDataPoint.symbol == position.symbol
                    ).order_by(MarketDataPoint.timestamp.desc()).first()
                    
                    if market_data:
                        position.current_price = market_data.close
                        position.unrealized_pnl = (market_data.close - position.average_price) * position.quantity
                        position.last_updated = datetime.utcnow()
                
                db.commit()
                
                # Update portfolio value
                db.execute(text("SELECT update_portfolio_value()"))
                db.commit()
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error updating positions: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in position update loop: {e}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "trading-service", "status": "running"}


@app.get("/health")
async def health():
    """Health check with details."""
    return {
        "status": "healthy",
        "service": "trading-service",
        "kafka_connected": kafka_consumer is not None
    }


@app.post("/orders", response_model=OrderModel)
async def create_order(order: OrderModel, background_tasks: BackgroundTasks):
    """Create a new trading order."""
    db = get_db_session()
    try:
        # Validate order
        if order.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        
        # Get execution price
        market_data = db.query(MarketDataPoint).filter(
            MarketDataPoint.symbol == order.symbol
        ).order_by(MarketDataPoint.timestamp.desc()).first()
        
        if not market_data:
            raise HTTPException(status_code=404, detail=f"No market data for {order.symbol}")
        
        price = order.price if order.price else market_data.close
        
        # Check risk limits
        can_execute, reason = check_risk_limits(
            order.symbol, order.side.value, order.quantity, price, db
        )
        
        if not can_execute:
            raise HTTPException(status_code=400, detail=reason)
        
        # Create order
        db_order = Order(
            order_id=order.order_id or str(uuid.uuid4()),
            symbol=order.symbol,
            side=order.side.value,
            order_type=order.order_type.value,
            quantity=order.quantity,
            price=order.price,
            status=order.status.value,
            timestamp=order.timestamp
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        
        # Execute order in background if market order
        if order.order_type.value == "MARKET":
            background_tasks.add_task(execute_order, db_order, db)
        
        return OrderModel(
            order_id=db_order.order_id,
            symbol=db_order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=db_order.quantity,
            price=db_order.price,
            status=order.status,
            timestamp=db_order.timestamp,
            filled_quantity=db_order.filled_quantity,
            average_fill_price=db_order.average_fill_price
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/orders/{order_id}", response_model=OrderModel)
async def get_order(order_id: str):
    """Get order by ID."""
    db = get_db_session()
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        from shared.models import OrderSide, OrderType, OrderStatus
        return OrderModel(
            order_id=order.order_id,
            symbol=order.symbol,
            side=OrderSide(order.side),
            order_type=OrderType(order.order_type),
            quantity=order.quantity,
            price=order.price,
            status=OrderStatus(order.status),
            timestamp=order.timestamp,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price
        )
    finally:
        db.close()


@app.get("/positions", response_model=List[PositionModel])
async def get_positions():
    """Get all positions."""
    db = get_db_session()
    try:
        positions = db.query(Position).all()
        return [
            PositionModel(
                symbol=p.symbol,
                quantity=p.quantity,
                average_price=p.average_price,
                current_price=p.current_price,
                unrealized_pnl=p.unrealized_pnl,
                realized_pnl=p.realized_pnl,
                last_updated=p.last_updated
            )
            for p in positions
        ]
    finally:
        db.close()


@app.get("/portfolio", response_model=PortfolioModel)
async def get_portfolio():
    """Get current portfolio."""
    db = get_db_session()
    try:
        account = db.query(Account).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        positions = db.query(Position).all()
        position_models = [
            PositionModel(
                symbol=p.symbol,
                quantity=p.quantity,
                average_price=p.average_price,
                current_price=p.current_price,
                unrealized_pnl=p.unrealized_pnl,
                realized_pnl=p.realized_pnl,
                last_updated=p.last_updated
            )
            for p in positions
        ]
        
        total_pnl = sum(p.unrealized_pnl + p.realized_pnl for p in positions)
        total_return = (account.total_value - settings.initial_capital) / settings.initial_capital
        
        return PortfolioModel(
            total_value=account.total_value,
            cash=account.cash,
            positions=position_models,
            total_pnl=total_pnl,
            total_return=total_return,
            timestamp=datetime.utcnow()
        )
    finally:
        db.close()


@app.get("/account")
async def get_account():
    """Get account information."""
    db = get_db_session()
    try:
        account = db.query(Account).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return {
            "cash": account.cash,
            "total_value": account.total_value,
            "initial_capital": settings.initial_capital,
            "total_return": (account.total_value - settings.initial_capital) / settings.initial_capital,
            "last_updated": account.last_updated
        }
    finally:
        db.close()


@app.get("/trades")
async def get_trades(limit: int = 100):
    """Get recent trades."""
    db = get_db_session()
    try:
        trades = db.query(Trade).order_by(Trade.timestamp.desc()).limit(limit).all()
        return [
            {
                "id": str(t.id),
                "order_id": str(t.order_id),
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "price": t.price,
                "commission": t.commission,
                "pnl": t.pnl,
                "timestamp": t.timestamp.isoformat()
            }
            for t in trades
        ]
    finally:
        db.close()


@app.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    """Cancel an order."""
    db = get_db_session()
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order.status not in ["PENDING", "PARTIALLY_FILLED"]:
            raise HTTPException(status_code=400, detail="Order cannot be cancelled")
        
        order.status = "CANCELLED"
        db.commit()
        
        return {"message": "Order cancelled", "order_id": order_id}
    finally:
        db.close()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.trading_service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )

