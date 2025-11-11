# System Architecture

## Overview

The Algorithmic Trading Platform is built using a microservices architecture, enabling scalability, maintainability, and independent deployment of components.

## Architecture Diagram

```
┌─────────────────┐
│  Market Data    │
│     APIs        │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Data Ingestion Service        │
│   - Real-time data collection   │
│   - Data normalization          │
└────────┬────────────────────────┘
         │
         ├─────────────────┐
         ▼                 ▼
    ┌─────────┐      ┌──────────┐
    │  Kafka  │      │PostgreSQL│
    │ Stream  │      │ Database │
    └────┬────┘      └────┬─────┘
         │                 │
         │                 │
         ▼                 │
┌─────────────────────────┘
│   ML Service            │
│   - Price Prediction    │
│   - Anomaly Detection   │
└────────┬────────────────┘
         │
         │ Trading Signals
         ▼
┌─────────────────────────┐
│   Trading Service       │
│   - Order Execution     │
│   - Portfolio Mgmt      │
│   - Risk Management     │
└────────┬────────────────┘
         │
         │
         ▼
┌─────────────────────────┐
│   Backtesting Service   │
│   - Strategy Testing    │
│   - Performance Analysis│
└─────────────────────────┘
```

## Components

### 1. Data Ingestion Service

**Purpose**: Collect and normalize real-time market data

**Responsibilities**:
- Fetch market data from APIs (yfinance, Alpaca)
- Normalize data format
- Store in database
- Publish to Kafka stream

**Technology**:
- FastAPI
- yfinance
- Kafka Producer
- PostgreSQL

**Data Flow**:
1. Scheduled data collection (every minute)
2. Data normalization
3. Database storage
4. Kafka publication

### 2. ML Service

**Purpose**: Generate trading signals and detect anomalies

**Responsibilities**:
- Price prediction using LSTM
- Anomaly detection using Isolation Forest
- Signal generation (BUY/SELL/HOLD)
- Model training and retraining

**Technology**:
- TensorFlow/Keras
- scikit-learn
- Kafka Consumer/Producer
- PostgreSQL

**Models**:
- **LSTM Price Predictor**: 3-layer LSTM with dropout
- **Anomaly Detector**: Isolation Forest with feature engineering

**Data Flow**:
1. Consume market data from Kafka
2. Generate predictions
3. Detect anomalies
4. Generate trading signals
5. Publish signals to Kafka

### 3. Trading Service

**Purpose**: Execute trades and manage portfolio

**Responsibilities**:
- Order execution
- Portfolio management
- Risk management
- Position tracking
- P&L calculation

**Technology**:
- FastAPI
- PostgreSQL with stored procedures
- Kafka Consumer
- ACID transactions

**Risk Management**:
- Position size limits
- Stop loss orders
- Take profit orders
- Cash availability checks
- Portfolio concentration limits

**Database Features**:
- Stored procedures for fund checks
- Triggers for portfolio updates
- Transaction management

### 4. Backtesting Service

**Purpose**: Test trading strategies on historical data

**Responsibilities**:
- Historical data retrieval
- Strategy simulation
- Performance metrics calculation
- Walk-forward analysis

**Technology**:
- FastAPI
- Pandas
- NumPy
- PostgreSQL

**Metrics Calculated**:
- Total return
- Sharpe ratio
- Maximum drawdown
- Win rate
- Average win/loss

## Data Flow

### Real-Time Trading Flow

1. **Data Collection**: Data Ingestion Service collects market data
2. **Storage**: Data stored in PostgreSQL (time-series optimized)
3. **Streaming**: Data published to Kafka topic `market_data`
4. **ML Processing**: ML Service consumes data, generates predictions
5. **Signal Generation**: Trading signals published to `trading_signals` topic
6. **Order Execution**: Trading Service consumes signals, executes orders
7. **Portfolio Update**: Positions and portfolio updated in database
8. **Monitoring**: Metrics exposed to Prometheus

### Anomaly Detection Flow

1. **Data Collection**: Same as trading flow
2. **Feature Extraction**: ML Service extracts features
3. **Anomaly Detection**: Isolation Forest model detects anomalies
4. **Alert Generation**: Anomalies published to `anomalies` topic
5. **Storage**: Anomalies stored in database
6. **Notification**: Alerts can trigger notifications

## Database Schema

### Core Tables

- **market_data**: Time-series market data
- **trading_signals**: ML-generated signals
- **anomalies**: Detected anomalies
- **orders**: Trading orders
- **positions**: Portfolio positions
- **trades**: Executed trades
- **portfolio_snapshots**: Portfolio value over time
- **account**: Account balance and value

### Stored Procedures

1. **check_available_funds**: Validates funds before order execution
2. **update_portfolio_value**: Updates portfolio value and creates snapshot
3. **calculate_position_pnl**: Calculates unrealized P&L for positions
4. **get_portfolio_stats**: Calculates portfolio statistics

### Triggers

1. **trigger_update_portfolio_value**: Auto-updates portfolio on position changes
2. **trigger_validate_order**: Validates order before insertion

## Message Queue (Kafka)

### Topics

- **market_data**: Real-time market data stream
- **trading_signals**: Trading signals from ML service
- **anomalies**: Anomaly detection alerts

### Consumer Groups

- `ml-service`: Consumes market_data
- `trading-service`: Consumes trading_signals

## API Endpoints

### Trading Service (Port 8000)

- `POST /orders`: Create order
- `GET /orders/{order_id}`: Get order
- `GET /positions`: Get all positions
- `GET /portfolio`: Get portfolio
- `GET /account`: Get account info
- `GET /trades`: Get recent trades

### ML Service (Port 8001)

- `POST /predict/{symbol}`: Get price prediction
- `POST /detect-anomaly/{symbol}`: Detect anomalies
- `POST /retrain`: Retrain models

### Data Ingestion (Port 8002)

- `POST /ingest/{symbol}`: Trigger data ingestion
- `GET /symbols`: Get tracked symbols

### Backtesting Service (Port 8003)

- `POST /backtest`: Run backtest
- `GET /backtest/portfolio-stats`: Get portfolio statistics
- `GET /backtest/strategies`: List available strategies

## Monitoring

### Prometheus Metrics

All services expose metrics at `/metrics`:
- Request counts
- Response times
- Error rates
- Custom business metrics

### Grafana Dashboards

Pre-configured dashboards for:
- Portfolio value over time
- Trading signals frequency
- Anomaly detection alerts
- Order execution metrics
- System health

## Scalability Considerations

### Horizontal Scaling

- **Stateless Services**: ML, Data Ingestion, Backtesting can scale horizontally
- **Stateful Services**: Trading Service should be single instance or use distributed locking

### Database Scaling

- Read replicas for analytics
- Partitioning for time-series data
- Connection pooling
- Query optimization

### Kafka Scaling

- Increase partitions for parallel processing
- Multiple brokers for high availability
- Consumer group scaling

## Security

### Authentication & Authorization

- API keys for service-to-service communication
- JWT tokens for user access (if frontend added)
- Role-based access control

### Data Security

- Encrypted database connections
- Encrypted Kafka messages
- Secure credential storage
- Audit logging

## Error Handling

### Retry Logic

- Exponential backoff for API calls
- Dead letter queues for failed messages
- Circuit breakers for external services

### Transaction Management

- ACID transactions for order execution
- Rollback on errors
- Idempotent operations

## Future Enhancements

1. **Real Broker Integration**: Connect to real trading APIs
2. **Advanced Strategies**: Implement more trading strategies
3. **Multi-Asset Support**: Extend to options, futures, crypto
4. **Reinforcement Learning**: RL-based strategy optimization
5. **Distributed Training**: Scale ML model training
6. **Real-time Dashboard**: Web-based frontend
7. **Mobile App**: Mobile notifications and monitoring

