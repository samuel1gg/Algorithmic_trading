"""Backtesting Service - Historical strategy testing."""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import text
from shared.config import settings
from shared.logger import setup_logger
from shared.database import get_db_session
from shared.models import BacktestResult
from database.models import MarketDataPoint
import yfinance as yf

logger = setup_logger(__name__)

app = FastAPI(
    title="Backtesting Service",
    description="Backtesting service for strategy testing",
    version="1.0.0"
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


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio."""
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    
    excess_returns = returns - risk_free_rate / 252
    sharpe = np.sqrt(252) * excess_returns.mean() / returns.std()
    return float(sharpe)


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Calculate maximum drawdown."""
    if len(equity_curve) == 0:
        return 0.0
    
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown = abs(drawdown.min())
    return float(max_drawdown)


def backtest_strategy(
    data: pd.DataFrame,
    initial_capital: float,
    strategy_func
) -> dict:
    """Run backtest on historical data."""
    capital = initial_capital
    cash = initial_capital
    positions = {}  # symbol -> quantity
    trades = []
    equity_curve = [initial_capital]
    
    for i in range(1, len(data)):
        current_data = data.iloc[:i+1]
        current_price = data.iloc[i]['close']
        current_date = data.index[i]
        
        # Get signal from strategy
        signal = strategy_func(current_data, i)
        
        if signal:
            action = signal.get('action')
            symbol = signal.get('symbol', 'STOCK')
            quantity = signal.get('quantity', 0)
            confidence = signal.get('confidence', 1.0)
            
            if action == 'BUY' and quantity > 0:
                cost = quantity * current_price
                commission = cost * 0.001  # 0.1% commission
                total_cost = cost + commission
                
                if cash >= total_cost:
                    cash -= total_cost
                    if symbol in positions:
                        positions[symbol] += quantity
                    else:
                        positions[symbol] = quantity
                    
                    trades.append({
                        'date': current_date,
                        'action': 'BUY',
                        'quantity': quantity,
                        'price': current_price,
                        'commission': commission
                    })
            
            elif action == 'SELL' and quantity > 0:
                if symbol in positions and positions[symbol] >= quantity:
                    revenue = quantity * current_price
                    commission = revenue * 0.001
                    net_revenue = revenue - commission
                    
                    cash += net_revenue
                    positions[symbol] -= quantity
                    
                    if positions[symbol] <= 0:
                        del positions[symbol]
                    
                    trades.append({
                        'date': current_date,
                        'action': 'SELL',
                        'quantity': quantity,
                        'price': current_price,
                        'commission': commission
                    })
        
        # Calculate current portfolio value
        positions_value = sum(positions.get(s, 0) * current_price for s in positions)
        total_value = cash + positions_value
        equity_curve.append(total_value)
    
    # Calculate final metrics
    final_capital = equity_curve[-1]
    total_return = (final_capital - initial_capital) / initial_capital
    
    # Calculate returns
    equity_series = pd.Series(equity_curve)
    returns = equity_series.pct_change().dropna()
    
    sharpe_ratio = calculate_sharpe_ratio(returns)
    max_drawdown = calculate_max_drawdown(equity_series)
    
    # Trade statistics
    if trades:
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win = np.mean([t.get('pnl', 0) for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.get('pnl', 0) for t in losing_trades]) if losing_trades else 0
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
    
    return {
        'initial_capital': initial_capital,
        'final_capital': final_capital,
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'total_trades': len(trades),
        'winning_trades': len(winning_trades) if trades else 0,
        'losing_trades': len(losing_trades) if trades else 0,
        'average_win': avg_win,
        'average_loss': avg_loss,
        'equity_curve': equity_curve,
        'trades': trades
    }


def simple_momentum_strategy(data: pd.DataFrame, current_idx: int) -> Optional[dict]:
    """Simple momentum strategy for backtesting."""
    if current_idx < 20:
        return None
    
    # Calculate moving averages
    short_ma = data['close'].rolling(window=10).mean().iloc[current_idx]
    long_ma = data['close'].rolling(window=20).mean().iloc[current_idx]
    current_price = data['close'].iloc[current_idx]
    
    # Buy signal: short MA crosses above long MA
    if short_ma > long_ma:
        # Calculate position size (10% of portfolio)
        portfolio_value = 100000  # Simplified
        position_value = portfolio_value * 0.1
        quantity = position_value / current_price
        
        return {
            'action': 'BUY',
            'quantity': round(quantity, 2),
            'confidence': 0.7
        }
    
    # Sell signal: short MA crosses below long MA
    elif short_ma < long_ma:
        # Sell all positions
        return {
            'action': 'SELL',
            'quantity': 100,  # Simplified
            'confidence': 0.7
        }
    
    return None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "backtesting-service", "status": "running"}


@app.get("/health")
async def health():
    """Health check with details."""
    return {
        "status": "healthy",
        "service": "backtesting-service"
    }


@app.post("/backtest", response_model=BacktestResult)
async def run_backtest(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float = 100000.0,
    strategy: str = "momentum"
):
    """Run backtest for a symbol and date range."""
    try:
        # Get historical data
        db = get_db_session()
        try:
            data_points = db.query(MarketDataPoint).filter(
                MarketDataPoint.symbol == symbol.upper(),
                MarketDataPoint.timestamp >= start_date,
                MarketDataPoint.timestamp <= end_date
            ).order_by(MarketDataPoint.timestamp).all()
            
            if len(data_points) < 50:
                # Fetch from yfinance if not enough data
                logger.info(f"Fetching data from yfinance for {symbol}")
                ticker = yf.Ticker(symbol)
                hist_data = ticker.history(start=start_date, end=end_date)
                
                if hist_data.empty:
                    raise HTTPException(status_code=404, detail=f"No data available for {symbol}")
                
                df = pd.DataFrame({
                    'open': hist_data['Open'],
                    'high': hist_data['High'],
                    'low': hist_data['Low'],
                    'close': hist_data['Close'],
                    'volume': hist_data['Volume']
                })
            else:
                # Use database data
                df = pd.DataFrame([{
                    'open': dp.open,
                    'high': dp.high,
                    'low': dp.low,
                    'close': dp.close,
                    'volume': dp.volume
                } for dp in data_points])
                df.index = pd.to_datetime([dp.timestamp for dp in data_points])
        finally:
            db.close()
        
        if len(df) < 50:
            raise HTTPException(status_code=400, detail="Not enough data for backtesting")
        
        # Select strategy
        if strategy == "momentum":
            strategy_func = simple_momentum_strategy
        else:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy}")
        
        # Run backtest
        results = backtest_strategy(df, initial_capital, strategy_func)
        
        return BacktestResult(
            strategy_name=strategy,
            start_date=start_date,
            end_date=end_date,
            initial_capital=results['initial_capital'],
            final_capital=results['final_capital'],
            total_return=results['total_return'],
            sharpe_ratio=results['sharpe_ratio'],
            max_drawdown=results['max_drawdown'],
            win_rate=results['win_rate'],
            total_trades=results['total_trades'],
            winning_trades=results['winning_trades'],
            losing_trades=results['losing_trades'],
            average_win=results['average_win'],
            average_loss=results['average_loss']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/backtest/portfolio-stats")
async def get_portfolio_stats(
    start_date: datetime,
    end_date: datetime
):
    """Get portfolio statistics using stored procedure."""
    db = get_db_session()
    try:
        result = db.execute(
            text("SELECT * FROM get_portfolio_stats(:start_date, :end_date)"),
            {"start_date": start_date, "end_date": end_date}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="No data available for date range")
        
        return {
            "total_return": float(result[0]) if result[0] else 0.0,
            "sharpe_ratio": float(result[1]) if result[1] else 0.0,
            "max_drawdown": float(result[2]) if result[2] else 0.0,
            "volatility": float(result[3]) if result[3] else 0.0,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    finally:
        db.close()


@app.get("/backtest/strategies")
async def get_available_strategies():
    """Get list of available backtesting strategies."""
    return {
        "strategies": [
            {
                "name": "momentum",
                "description": "Simple moving average crossover strategy",
                "parameters": {}
            }
        ]
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.backtesting_service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )

