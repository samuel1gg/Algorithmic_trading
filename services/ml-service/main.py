"""ML Service - Price prediction and anomaly detection."""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import uvicorn
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from shared.config import settings
from shared.logger import setup_logger
from shared.kafka_client import KafkaProducerClient, KafkaConsumerClient
from shared.database import get_db_session
from shared.models import TradingSignal, AnomalyAlert, MarketData
from database.models import MarketDataPoint, TradingSignal as DBTradingSignal, Anomaly as DBAnomaly
from models import PricePredictor, AnomalyDetector
import threading
import time

logger = setup_logger(__name__)

# Global models and clients
price_predictor = None
anomaly_detector = None
kafka_producer = None
kafka_consumer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global price_predictor, anomaly_detector, kafka_producer, kafka_consumer
    
    # Initialize models
    price_predictor = PricePredictor(sequence_length=settings.lstm_sequence_length)
    anomaly_detector = AnomalyDetector(contamination=settings.anomaly_detection_threshold)
    
    # Initialize Kafka
    kafka_producer = KafkaProducerClient()
    kafka_consumer = KafkaConsumerClient(
        topics=[settings.kafka_topic_market_data],
        group_id="ml-service"
    )
    
    # Train models if needed
    asyncio.create_task(train_models_if_needed())
    
    # Start background processing
    background_thread = threading.Thread(target=process_market_data_stream, daemon=True)
    background_thread.start()
    
    logger.info("ML service started")
    yield
    
    if kafka_consumer:
        kafka_consumer.close()
    if kafka_producer:
        kafka_producer.close()
    logger.info("ML service stopped")


app = FastAPI(
    title="ML Service",
    description="Machine learning service for price prediction and anomaly detection",
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


async def train_models_if_needed():
    """Train models with historical data if they don't exist."""
    try:
        db = get_db_session()
        try:
            # Get historical data
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            data_points = db.query(MarketDataPoint).filter(
                MarketDataPoint.timestamp >= cutoff_date,
                MarketDataPoint.symbol == "AAPL"
            ).order_by(MarketDataPoint.timestamp).all()
            
            if len(data_points) >= 100:  # Need minimum data
                df = pd.DataFrame([{
                    'timestamp': dp.timestamp,
                    'open': dp.open,
                    'high': dp.high,
                    'low': dp.low,
                    'close': dp.close,
                    'volume': dp.volume
                } for dp in data_points])
                
                # Train models
                if price_predictor:
                    price_predictor.train(df, epochs=20)
                if anomaly_detector:
                    anomaly_detector.train(df)
                
                logger.info("Models trained with historical data")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error training models: {e}")


def process_market_data_stream():
    """Process incoming market data stream."""
    def process_message(message: dict, key: Optional[str]):
        try:
            market_data = MarketData(**message)
            
            # Get historical data for prediction
            db = get_db_session()
            try:
                cutoff_time = datetime.fromisoformat(market_data.timestamp) - timedelta(hours=1)
                historical_data = db.query(MarketDataPoint).filter(
                    MarketDataPoint.symbol == market_data.symbol,
                    MarketDataPoint.timestamp >= cutoff_time
                ).order_by(MarketDataPoint.timestamp).all()
                
                if len(historical_data) >= price_predictor.sequence_length:
                    # Prepare DataFrame
                    df = pd.DataFrame([{
                        'timestamp': dp.timestamp,
                        'open': dp.open,
                        'high': dp.high,
                        'low': dp.low,
                        'close': dp.close,
                        'volume': dp.volume
                    } for dp in historical_data])
                    
                    # Generate trading signal
                    generate_trading_signal(market_data, df)
                    
                    # Detect anomalies
                    detect_anomalies(market_data, df)
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
    
    while True:
        try:
            kafka_consumer.consume(process_message)
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
            time.sleep(5)


def generate_trading_signal(market_data: MarketData, historical_df: pd.DataFrame):
    """Generate trading signal based on prediction."""
    try:
        # Predict next price
        predicted_price = price_predictor.predict(historical_df)
        current_price = market_data.close
        
        # Calculate confidence based on prediction vs current
        price_change = (predicted_price - current_price) / current_price
        confidence = min(abs(price_change) * 10, 1.0)  # Normalize to 0-1
        
        # Determine action
        if price_change > 0.01 and confidence >= settings.min_confidence_threshold:
            action = "BUY"
        elif price_change < -0.01 and confidence >= settings.min_confidence_threshold:
            action = "SELL"
        else:
            action = "HOLD"
        
        # Calculate stop loss and take profit
        stop_loss = None
        take_profit = None
        if action != "HOLD":
            if action == "BUY":
                stop_loss = current_price * (1 - settings.stop_loss_percentage)
                take_profit = current_price * (1 + settings.take_profit_percentage)
            else:  # SELL
                stop_loss = current_price * (1 + settings.stop_loss_percentage)
                take_profit = current_price * (1 - settings.take_profit_percentage)
        
        signal = TradingSignal(
            symbol=market_data.symbol,
            timestamp=datetime.fromisoformat(market_data.timestamp),
            action=action,
            confidence=confidence,
            predicted_price=predicted_price,
            current_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            model_version="v1.0"
        )
        
        # Store in database
        db = get_db_session()
        try:
            db_signal = DBTradingSignal(
                symbol=signal.symbol,
                timestamp=signal.timestamp,
                action=signal.action,
                confidence=signal.confidence,
                predicted_price=signal.predicted_price,
                current_price=signal.current_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                model_version=signal.model_version
            )
            db.add(db_signal)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing signal: {e}")
        finally:
            db.close()
        
        # Publish to Kafka
        if kafka_producer and action != "HOLD":
            kafka_producer.send(
                settings.kafka_topic_trading_signals,
                signal.dict(),
                key=signal.symbol
            )
            logger.info(f"Generated {action} signal for {signal.symbol} with confidence {confidence:.2f}")
            
    except Exception as e:
        logger.error(f"Error generating trading signal: {e}")


def detect_anomalies(market_data: MarketData, historical_df: pd.DataFrame):
    """Detect anomalies in market data."""
    try:
        is_anomaly, anomaly_score = anomaly_detector.detect(historical_df)
        
        if is_anomaly:
            # Determine anomaly type
            recent_returns = historical_df['close'].pct_change().tail(5).mean()
            volume_change = historical_df['volume'].pct_change().tail(5).mean()
            
            if abs(recent_returns) > 0.05:
                anomaly_type = "PRICE_SPIKE"
                severity = "HIGH" if abs(recent_returns) > 0.1 else "MEDIUM"
            elif abs(volume_change) > 0.5:
                anomaly_type = "VOLUME_SPIKE"
                severity = "MEDIUM"
            else:
                anomaly_type = "UNUSUAL_PATTERN"
                severity = "LOW"
            
            alert = AnomalyAlert(
                symbol=market_data.symbol,
                timestamp=datetime.fromisoformat(market_data.timestamp),
                anomaly_score=anomaly_score,
                anomaly_type=anomaly_type,
                description=f"Detected {anomaly_type} for {market_data.symbol}",
                severity=severity,
                market_data=market_data
            )
            
            # Store in database
            db = get_db_session()
            try:
                db_anomaly = DBAnomaly(
                    symbol=alert.symbol,
                    timestamp=alert.timestamp,
                    anomaly_score=alert.anomaly_score,
                    anomaly_type=alert.anomaly_type,
                    description=alert.description,
                    severity=alert.severity
                )
                db.add(db_anomaly)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error storing anomaly: {e}")
            finally:
                db.close()
            
            # Publish to Kafka
            if kafka_producer:
                kafka_producer.send(
                    settings.kafka_topic_anomalies,
                    alert.dict(),
                    key=alert.symbol
                )
                logger.warning(f"Anomaly detected for {alert.symbol}: {anomaly_type} ({severity})")
                
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "ml-service", "status": "running"}


@app.get("/health")
async def health():
    """Health check with details."""
    return {
        "status": "healthy",
        "service": "ml-service",
        "models_loaded": price_predictor is not None and anomaly_detector is not None
    }


@app.post("/predict/{symbol}")
async def predict_price(symbol: str):
    """Get price prediction for a symbol."""
    try:
        db = get_db_session()
        try:
            # Get recent data
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            data_points = db.query(MarketDataPoint).filter(
                MarketDataPoint.symbol == symbol.upper(),
                MarketDataPoint.timestamp >= cutoff_time
            ).order_by(MarketDataPoint.timestamp).all()
            
            if len(data_points) < price_predictor.sequence_length:
                raise HTTPException(
                    status_code=400,
                    detail=f"Not enough data. Need at least {price_predictor.sequence_length} data points"
                )
            
            df = pd.DataFrame([{
                'timestamp': dp.timestamp,
                'open': dp.open,
                'high': dp.high,
                'low': dp.low,
                'close': dp.close,
                'volume': dp.volume
            } for dp in data_points])
            
            predicted_price = price_predictor.predict(df)
            current_price = data_points[-1].close
            
            return {
                "symbol": symbol.upper(),
                "current_price": current_price,
                "predicted_price": predicted_price,
                "expected_change": ((predicted_price - current_price) / current_price) * 100
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect-anomaly/{symbol}")
async def detect_anomaly(symbol: str):
    """Manually trigger anomaly detection for a symbol."""
    try:
        db = get_db_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            data_points = db.query(MarketDataPoint).filter(
                MarketDataPoint.symbol == symbol.upper(),
                MarketDataPoint.timestamp >= cutoff_time
            ).order_by(MarketDataPoint.timestamp).all()
            
            if len(data_points) < 10:
                raise HTTPException(status_code=400, detail="Not enough data for anomaly detection")
            
            df = pd.DataFrame([{
                'timestamp': dp.timestamp,
                'open': dp.open,
                'high': dp.high,
                'low': dp.low,
                'close': dp.close,
                'volume': dp.volume
            } for dp in data_points])
            
            is_anomaly, score = anomaly_detector.detect(df)
            
            return {
                "symbol": symbol.upper(),
                "is_anomaly": is_anomaly,
                "anomaly_score": score,
                "threshold": settings.anomaly_detection_threshold
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrain")
async def retrain_models(background_tasks: BackgroundTasks):
    """Trigger model retraining."""
    background_tasks.add_task(train_models_if_needed)
    return {"message": "Model retraining queued"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.ml_service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )

