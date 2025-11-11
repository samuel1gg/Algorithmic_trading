# Detailed System Architecture

## Table of Contents
1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Sequence Diagrams](#sequence-diagrams)
5. [Database Schema Details](#database-schema-details)
6. [API Contracts](#api-contracts)
7. [Message Queue Architecture](#message-queue-architecture)
8. [Deployment Architecture](#deployment-architecture)

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Data Sources                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  yfinance   │  │   Alpaca    │  │  Other APIs  │          │
│  │   (Free)    │  │  (Real Data)│  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                             ▼
          ┌──────────────────────────────────────┐
          │   Data Ingestion Service              │
          │   - Fetches market data               │
          │   - Normalizes format                 │
          │   - Schedules collection              │
          └──────────────┬───────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
┌──────────────────┐          ┌──────────────────┐
│   PostgreSQL     │          │   Apache Kafka    │
│   (Storage)      │          │   (Streaming)    │
└────────┬─────────┘          └────────┬──────────┘
         │                             │
         │                             │
         └──────────────┬──────────────┘
                        │
                        ▼
          ┌─────────────────────────────┐
          │    ML Service               │
          │   - Price Prediction (LSTM)  │
          │   - Anomaly Detection       │
          │   - Signal Generation       │
          └──────────────┬──────────────┘
                         │
                         │ Trading Signals
                         ▼
          ┌─────────────────────────────┐
          │   Trading Service            │
          │   - Order Execution          │
          │   - Risk Management          │
          │   - Portfolio Management     │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌─────────────────────────────┐
          │   PostgreSQL                │
          │   - Orders, Trades          │
          │   - Positions, Portfolio    │
          └─────────────────────────────┘

          ┌─────────────────────────────┐
          │   Backtesting Service       │
          │   - Historical Testing      │
          │   - Performance Metrics     │
          │   (Reads from PostgreSQL)    │
          └─────────────────────────────┘
```

## Component Architecture

### 1. Data Ingestion Service

**Purpose**: Collect market data from external APIs

**Components**:
```
Data Ingestion Service
├── API Clients
│   ├── yfinance client (free market data)
│   └── Alpaca client (real trading data)
├── Scheduler
│   └── Runs every 1 minute per symbol
├── Data Normalizer
│   └── Converts API responses to standard format
├── Database Writer
│   └── Stores data in PostgreSQL
└── Kafka Producer
    └── Publishes to market_data topic
```

**How Market Data Comes In**:

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: Scheduled Task (Every 1 minute)                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  schedule.every(1).minutes.do(                   │   │
│  │      process_and_store_market_data,             │   │
│  │      symbol="AAPL"                              │   │
│  │  )                                               │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: Fetch from API                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  ticker = yf.Ticker("AAPL")                      │   │
│  │  data = ticker.history(period="1d",              │   │
│  │                       interval="1m")             │   │
│  │  # Returns: OHLCV data for last day              │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: Normalize Data                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  market_data = {                                 │   │
│  │    "symbol": "AAPL",                             │   │
│  │    "timestamp": "2024-01-15T10:30:00Z",          │   │
│  │    "open": 150.0,                                 │   │
│  │    "high": 152.0,                                │   │
│  │    "low": 149.0,                                 │   │
│  │    "close": 151.0,                               │   │
│  │    "volume": 1000000                             │   │
│  │  }                                                │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌──────────────┐      ┌──────────────────┐
│  PostgreSQL  │      │   Kafka Topic     │
│  (Storage)   │      │  market_data      │
└──────────────┘      └──────────────────┘
```

**Who Initiates the Request?**
- **Data Ingestion Service** initiates requests to market APIs
- Uses Python `schedule` library to run every minute
- No external client calls the data ingestion service to fetch data
- It's a **scheduled background job** that runs automatically

**API Request Flow**:
```python
# In data-ingestion/main.py
def process_and_store_market_data(symbol: str = "AAPL"):
    # 1. Data Ingestion Service makes HTTP request to yfinance
    ticker = yf.Ticker(symbol)  # This calls yfinance API
    data = ticker.history(...)   # HTTP GET request happens here
    
    # 2. Process the response
    market_data = normalize(data)
    
    # 3. Store and publish
    store_in_db(market_data)
    publish_to_kafka(market_data)
```

### 2. ML Service

**Purpose**: Generate trading signals and detect anomalies

**Components**:
```
ML Service
├── Price Predictor (LSTM)
│   ├── Model Loader
│   ├── Feature Extractor
│   ├── Predictor
│   └── Model Trainer
├── Anomaly Detector (Isolation Forest)
│   ├── Feature Extractor
│   ├── Detector
│   └── Model Trainer
├── Signal Generator
│   └── Converts predictions to BUY/SELL/HOLD
└── Kafka Consumer/Producer
    ├── Consumes: market_data
    └── Produces: trading_signals, anomalies
```

**Data Flow**:
```
Kafka (market_data) 
    → ML Service consumes
    → Get historical data from DB
    → LSTM predicts next price
    → Generate signal (BUY/SELL/HOLD)
    → Publish to Kafka (trading_signals)
```

### 3. Trading Service

**Purpose**: Execute trades and manage portfolio

**Components**:
```
Trading Service
├── Order Manager
│   ├── Order Validator
│   ├── Order Executor
│   └── Order Status Tracker
├── Risk Manager
│   ├── Position Size Checker
│   ├── Cash Availability Checker
│   ├── Stop-Loss Manager
│   └── Take-Profit Manager
├── Portfolio Manager
│   ├── Position Tracker
│   ├── P&L Calculator
│   └── Portfolio Value Calculator
└── Kafka Consumer
    └── Consumes: trading_signals
```

### 4. Backtesting Service

**Purpose**: Test strategies on historical data

**Components**:
```
Backtesting Service
├── Historical Data Loader
│   └── Reads from PostgreSQL
├── Strategy Simulator
│   └── Replays historical market
├── Performance Calculator
│   ├── Return Calculator
│   ├── Sharpe Ratio Calculator
│   ├── Drawdown Calculator
│   └── Win Rate Calculator
└── Report Generator
    └── Returns backtest results
```

## Data Flow Diagrams

### Real-Time Trading Flow

```
┌──────────────┐
│ Market APIs  │
└──────┬───────┘
       │ HTTP GET (every 1 min)
       ▼
┌──────────────────┐
│ Data Ingestion   │──┐
│ - Fetch data     │  │ Store in DB
│ - Normalize      │  │
│ - Store          │──┘
└──────┬───────────┘
       │ Publish to Kafka
       ▼
┌──────────────────┐
│  Kafka Topic:    │
│  market_data     │
└──────┬───────────┘
       │
       │ Consume
       ▼
┌──────────────────┐
│  ML Service      │──┐
│ - Get historical │  │ Query DB for
│ - Predict price  │  │ last 30 points
│ - Generate signal│  │
└──────┬───────────┘──┘
       │ Publish signal
       ▼
┌──────────────────┐
│  Kafka Topic:    │
│  trading_signals │
└──────┬───────────┘
       │
       │ Consume
       ▼
┌──────────────────┐
│ Trading Service  │──┐
│ - Check risk     │  │ Query DB for
│ - Execute order  │  │ account/positions
│ - Update portfolio│  │
└───────────────────┘──┘
```

### Anomaly Detection Flow

```
Market Data → ML Service
                │
                ├─→ Extract features
                ├─→ Isolation Forest
                ├─→ Detect anomaly?
                │
                ├─→ YES → Publish to Kafka (anomalies topic)
                │         Store in DB
                │
                └─→ NO → Continue
```

## Sequence Diagrams

### Complete Trading Flow Sequence

```
Market API    Data Ingestion    Kafka        PostgreSQL    ML Service    Trading Service
    │              │              │              │              │              │
    │              │──Schedule──>│              │              │              │
    │              │              │              │              │              │
    │<──HTTP GET───│              │              │              │              │
    │──Response───>│              │              │              │              │
    │              │              │              │              │              │
    │              │──Store──────>│              │              │              │
    │              │              │              │              │              │
    │              │──Publish────>│              │              │              │
    │              │              │              │              │              │
    │              │              │<──Consume────│              │              │
    │              │              │              │              │              │
    │              │              │              │<──Query───────│              │
    │              │              │              │──Response───>│              │
    │              │              │              │              │              │
    │              │              │              │              │──Predict─────>│
    │              │              │              │              │──Signal──────>│
    │              │              │              │              │              │
    │              │              │<──Publish─────│              │              │
    │              │              │              │              │              │
    │              │              │              │              │              │<──Consume
    │              │              │              │              │              │
    │              │              │              │<──Query───────│              │
    │              │              │              │──Response───>│              │
    │              │              │              │              │              │
    │              │              │              │              │              │──Execute
    │              │              │              │<──Update──────│              │
    │              │              │              │              │              │
```

## Database Schema Details

### Core Tables

#### market_data
```sql
CREATE TABLE market_data (
    id UUID PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume INTEGER NOT NULL,
    vwap FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_market_data_symbol_timestamp ON market_data(symbol, timestamp);
CREATE INDEX idx_market_data_timestamp ON market_data(timestamp);
```

#### orders
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- BUY/SELL
    order_type VARCHAR(10) NOT NULL,  -- MARKET/LIMIT/STOP
    quantity FLOAT NOT NULL,
    price FLOAT,  -- For limit orders
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    filled_quantity FLOAT DEFAULT 0.0,
    average_fill_price FLOAT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    filled_at TIMESTAMP WITH TIME ZONE
);
```

#### positions
```sql
CREATE TABLE positions (
    id UUID PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    quantity FLOAT NOT NULL,
    average_price FLOAT NOT NULL,
    current_price FLOAT NOT NULL,
    unrealized_pnl FLOAT DEFAULT 0.0,
    realized_pnl FLOAT DEFAULT 0.0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Stored Procedures

#### check_available_funds
```sql
FUNCTION check_available_funds(
    p_order_id UUID,
    p_symbol VARCHAR,
    p_side VARCHAR,
    p_quantity FLOAT,
    p_price FLOAT
) RETURNS BOOLEAN
-- Checks if account has enough cash for buy orders
-- Checks if position has enough quantity for sell orders
```

#### update_portfolio_value
```sql
FUNCTION update_portfolio_value() RETURNS TRIGGER
-- Called automatically when positions change
-- Calculates total portfolio value
-- Creates portfolio snapshot
```

## API Contracts

### Data Ingestion Service

**POST /ingest/{symbol}**
- Manually trigger data collection for a symbol
- Response: `{"message": "Ingestion triggered", "status": "queued"}`

**GET /symbols**
- Get list of tracked symbols
- Response: `{"symbols": ["AAPL", "MSFT", ...], "update_frequency": "1 minute"}`

### ML Service

**POST /predict/{symbol}**
- Get price prediction for symbol
- Response: `{"symbol": "AAPL", "current_price": 150.0, "predicted_price": 155.0, "expected_change": 3.33}`

**POST /detect-anomaly/{symbol}**
- Detect anomalies for symbol
- Response: `{"symbol": "AAPL", "is_anomaly": true, "anomaly_score": -0.5}`

### Trading Service

**POST /orders**
- Create new order
- Request: `{"symbol": "AAPL", "side": "BUY", "order_type": "MARKET", "quantity": 10.0}`
- Response: Order object

**GET /portfolio**
- Get current portfolio
- Response: `{"total_value": 105000.0, "cash": 50000.0, "positions": [...], "total_pnl": 5000.0}`

### Backtesting Service

**POST /backtest**
- Run backtest
- Query params: `symbol`, `start_date`, `end_date`, `initial_capital`, `strategy`
- Response: BacktestResult with all metrics

## Message Queue Architecture

### Kafka Topics

#### market_data
- **Producer**: Data Ingestion Service
- **Consumers**: ML Service
- **Message Format**:
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-01-15T10:30:00Z",
  "open": 150.0,
  "high": 152.0,
  "low": 149.0,
  "close": 151.0,
  "volume": 1000000
}
```

#### trading_signals
- **Producer**: ML Service
- **Consumers**: Trading Service
- **Message Format**:
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-01-15T10:31:00Z",
  "action": "BUY",
  "confidence": 0.85,
  "predicted_price": 155.0,
  "current_price": 151.0,
  "stop_loss": 148.0,
  "take_profit": 158.5
}
```

#### anomalies
- **Producer**: ML Service
- **Consumers**: (Can be monitoring/alerting service)
- **Message Format**:
```json
{
  "symbol": "AAPL",
  "timestamp": "2024-01-15T10:30:00Z",
  "anomaly_score": -0.5,
  "anomaly_type": "PRICE_SPIKE",
  "severity": "HIGH",
  "description": "Detected PRICE_SPIKE for AAPL"
}
```

### Consumer Groups

- **ml-service**: Consumes `market_data`
- **trading-service**: Consumes `trading_signals`

## Deployment Architecture

### Docker Compose Services

```
┌─────────────────────────────────────────┐
│  Docker Network: trading_network       │
│                                         │
│  ┌──────────────┐  ┌──────────────┐    │
│  │  PostgreSQL  │  │   Zookeeper  │    │
│  │  Port: 5432  │  │  Port: 2181 │    │
│  └──────┬───────┘  └──────┬───────┘    │
│         │                 │            │
│         │                 ▼            │
│         │         ┌──────────────┐    │
│         │         │    Kafka    │    │
│         │         │  Port: 9092 │    │
│         │         └──────────────┘    │
│         │                              │
│         │  ┌──────────────────────┐   │
│         │  │ Data Ingestion       │   │
│         │  │ Port: 8002           │   │
│         │  └──────────────────────┘   │
│         │                              │
│         │  ┌──────────────────────┐   │
│         │  │ ML Service           │   │
│         │  │ Port: 8001           │   │
│         │  └──────────────────────┘   │
│         │                              │
│         │  ┌──────────────────────┐   │
│         │  │ Trading Service      │   │
│         │  │ Port: 8000           │   │
│         │  └──────────────────────┘   │
│         │                              │
│         │  ┌──────────────────────┐   │
│         │  │ Backtesting Service  │   │
│         │  │ Port: 8003           │   │
│         │  └──────────────────────┘   │
│         │                              │
│         │  ┌──────────────────────┐   │
│         │  │ Prometheus            │   │
│         │  │ Port: 9090            │   │
│         │  └──────────────────────┘   │
│         │                              │
│         │  ┌──────────────────────┐   │
│         │  │ Grafana              │   │
│         │  │ Port: 3000           │   │
│         │  └──────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

## How Market Data API Requests Work

### Step-by-Step Flow

1. **Scheduler Triggers** (Every 1 minute)
   ```python
   # In data-ingestion/main.py
   schedule.every(1).minutes.do(process_and_store_market_data, symbol="AAPL")
   ```

2. **Service Makes HTTP Request**
   ```python
   ticker = yf.Ticker("AAPL")  # Creates yfinance client
   data = ticker.history(period="1d", interval="1m")  # HTTP GET to yfinance API
   ```

3. **API Response**
   ```python
   # yfinance returns pandas DataFrame with OHLCV data
   # Example response:
   #            Open    High     Low   Close    Volume
   # 2024-01-15 150.0  152.0   149.0  151.0   1000000
   ```

4. **Data Processing**
   ```python
   # Normalize to standard format
   market_data = {
       "symbol": "AAPL",
       "timestamp": datetime.utcnow(),
       "open": 150.0,
       "high": 152.0,
       "low": 149.0,
       "close": 151.0,
       "volume": 1000000
   }
   ```

5. **Storage & Publishing**
   ```python
   # Store in PostgreSQL
   db.add(MarketDataPoint(...))
   
   # Publish to Kafka
   kafka_producer.send("market_data", market_data)
   ```

### Who Calls What?

```
┌─────────────────────────────────────────┐
│  NO EXTERNAL CLIENT                    │
│  Data Ingestion is a BACKGROUND JOB    │
└─────────────────────────────────────────┘

Data Ingestion Service (Internal)
    │
    │ Scheduled (every 1 min)
    │
    ▼
yfinance API (External)
    │
    │ HTTP GET Request
    │
    ▼
yfinance API Response
    │
    │ OHLCV Data
    │
    ▼
Data Ingestion Service
    │
    ├─→ PostgreSQL (Store)
    └─→ Kafka (Publish)
```

**Key Point**: The Data Ingestion Service is **self-contained** and **self-triggering**. It doesn't wait for external requests - it runs on a schedule.

## Summary

- **Backtesting**: Tests strategies on historical data (before risking money)
- **Live Trading**: Executes trades in real-time (actual money)
- **Market Data**: Data Ingestion Service automatically fetches from APIs every minute
- **Architecture**: Microservices with Kafka for async communication
- **Database**: PostgreSQL with stored procedures for business logic
- **APIs**: RESTful endpoints for each service

