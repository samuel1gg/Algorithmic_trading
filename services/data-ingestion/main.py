"""Data Ingestion Service - Real-time market data ingestion."""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import uvicorn
from shared.config import settings
from shared.logger import setup_logger
from shared.kafka_client import KafkaProducerClient
from shared.database import get_db_session
from database.models import MarketDataPoint
from datetime import datetime
import yfinance as yf
import schedule
import threading
import time

logger = setup_logger(__name__)

# Global producer
kafka_producer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global kafka_producer
    kafka_producer = KafkaProducerClient()
    logger.info("Data ingestion service started")
    
    # Start background data collection
    background_thread = threading.Thread(target=run_scheduled_tasks, daemon=True)
    background_thread.start()
    
    yield
    
    if kafka_producer:
        kafka_producer.close()
    logger.info("Data ingestion service stopped")


app = FastAPI(
    title="Data Ingestion Service",
    description="Real-time market data ingestion service",
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


def fetch_market_data(symbol: str = "AAPL"):
    """Fetch market data for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")
        
        if data.empty:
            logger.warning(f"No data available for {symbol}")
            return None
        
        # Get latest data point
        latest = data.iloc[-1]
        
        market_data = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "close": float(latest["Close"]),
            "volume": int(latest["Volume"]),
            "vwap": float((latest["High"] + latest["Low"] + latest["Close"]) / 3)
        }
        
        return market_data
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None


def process_and_store_market_data(symbol: str = "AAPL"):
    """Process market data and store in database and Kafka."""
    market_data = fetch_market_data(symbol)
    
    if not market_data:
        return
    
    try:
        # Store in database
        db = get_db_session()
        try:
            data_point = MarketDataPoint(
                symbol=market_data["symbol"],
                timestamp=datetime.fromisoformat(market_data["timestamp"]),
                open=market_data["open"],
                high=market_data["high"],
                low=market_data["low"],
                close=market_data["close"],
                volume=market_data["volume"],
                vwap=market_data.get("vwap")
            )
            db.add(data_point)
            db.commit()
            logger.debug(f"Stored market data for {symbol}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing in database: {e}")
        finally:
            db.close()
        
        # Publish to Kafka
        if kafka_producer:
            kafka_producer.send(
                settings.kafka_topic_market_data,
                market_data,
                key=symbol
            )
            logger.debug(f"Published market data for {symbol} to Kafka")
            
    except Exception as e:
        logger.error(f"Error processing market data: {e}")


def run_scheduled_tasks():
    """Run scheduled data collection tasks."""
    # Schedule data collection every minute for multiple symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    for symbol in symbols:
        schedule.every(1).minutes.do(process_and_store_market_data, symbol=symbol)
    
    # Run immediately
    for symbol in symbols:
        process_and_store_market_data(symbol)
    
    while True:
        schedule.run_pending()
        time.sleep(1)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "data-ingestion", "status": "running"}


@app.get("/health")
async def health():
    """Health check with details."""
    return {
        "status": "healthy",
        "service": "data-ingestion",
        "kafka_connected": kafka_producer is not None
    }


@app.post("/ingest/{symbol}")
async def ingest_symbol(symbol: str, background_tasks: BackgroundTasks):
    """Manually trigger data ingestion for a symbol."""
    background_tasks.add_task(process_and_store_market_data, symbol=symbol.upper())
    return {"message": f"Ingestion triggered for {symbol}", "status": "queued"}


@app.get("/symbols")
async def get_symbols():
    """Get list of symbols being tracked."""
    return {
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
        "update_frequency": "1 minute"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.data_ingestion_port,
        reload=True,
        log_level=settings.log_level.lower()
    )

