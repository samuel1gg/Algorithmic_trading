# Component-Level Architecture

## Detailed Component Breakdown

### Data Ingestion Service Components

```
Data Ingestion Service
│
├── main.py (Entry Point)
│   ├── FastAPI App
│   ├── Background Scheduler
│   └── API Endpoints
│
├── Data Collection Module
│   ├── yfinance_client.py
│   │   └── fetch_market_data(symbol)
│   │       └── HTTP GET → yfinance API
│   │
│   └── alpaca_client.py (Optional)
│       └── fetch_market_data(symbol)
│           └── HTTP GET → Alpaca API
│
├── Data Processing Module
│   └── normalizer.py
│       └── normalize_api_response(data)
│           └── Convert to standard format
│
├── Storage Module
│   └── database_writer.py
│       └── store_market_data(data)
│           └── SQLAlchemy ORM → PostgreSQL
│
└── Messaging Module
    └── kafka_producer.py
        └── publish_market_data(data)
            └── Kafka Producer → market_data topic
```

**Request Flow**:
```
Scheduler (Python schedule library)
    │
    │ Every 1 minute
    │
    ▼
fetch_market_data("AAPL")
    │
    │ HTTP GET Request
    │
    ▼
yfinance API
    │
    │ JSON/CSV Response
    │
    ▼
normalize_api_response()
    │
    │ Standard format
    │
    ├─→ store_market_data() → PostgreSQL
    └─→ publish_market_data() → Kafka
```

### ML Service Components

```
ML Service
│
├── main.py (Entry Point)
│   ├── FastAPI App
│   ├── Kafka Consumer (market_data)
│   ├── Kafka Producer (trading_signals, anomalies)
│   └── API Endpoints
│
├── Models Module
│   ├── price_predictor.py
│   │   ├── LSTM Model
│   │   ├── train()
│   │   ├── predict()
│   │   └── load_model()
│   │
│   └── anomaly_detector.py
│       ├── Isolation Forest Model
│       ├── train()
│       ├── detect()
│       └── extract_features()
│
├── Signal Generator
│   └── signal_generator.py
│       └── generate_signal(prediction, current_price)
│           ├── Calculate confidence
│           ├── Determine action (BUY/SELL/HOLD)
│           └── Calculate stop_loss/take_profit
│
└── Data Access
    └── historical_data_loader.py
        └── get_historical_data(symbol, lookback_period)
            └── SQLAlchemy Query → PostgreSQL
```

**Processing Flow**:
```
Kafka Consumer receives market_data
    │
    ▼
Get last 30 data points from PostgreSQL
    │
    ▼
LSTM Model predicts next price
    │
    ▼
Signal Generator creates trading signal
    │
    ├─→ If action != HOLD
    │   └─→ Publish to Kafka (trading_signals)
    │
    └─→ Anomaly Detector checks for anomalies
        │
        ├─→ If anomaly detected
        │   └─→ Publish to Kafka (anomalies)
        │
        └─→ Store in PostgreSQL
```

### Trading Service Components

```
Trading Service
│
├── main.py (Entry Point)
│   ├── FastAPI App
│   ├── Kafka Consumer (trading_signals)
│   ├── Background Position Updater
│   └── API Endpoints
│
├── Order Management
│   ├── order_validator.py
│   │   └── validate_order(order)
│   │
│   ├── order_executor.py
│   │   └── execute_order(order)
│   │       ├── Get current market price
│   │       ├── Check limit order conditions
│   │       ├── Update order status
│   │       └── Create trade record
│   │
│   └── order_manager.py
│       └── create_order(signal)
│
├── Risk Management
│   ├── risk_checker.py
│   │   └── check_risk_limits(symbol, side, quantity, price)
│   │       ├── Check available cash (for BUY)
│   │       ├── Check available position (for SELL)
│   │       ├── Check position size limits
│   │       └── Call stored procedure: check_available_funds()
│   │
│   ├── stop_loss_manager.py
│   │   └── check_stop_loss(position)
│   │
│   └── take_profit_manager.py
│       └── check_take_profit(position)
│
├── Portfolio Management
│   ├── position_manager.py
│   │   ├── update_position(symbol, quantity, price)
│   │   ├── create_position(symbol, quantity, price)
│   │   └── close_position(symbol)
│   │
│   ├── portfolio_calculator.py
│   │   ├── calculate_portfolio_value()
│   │   ├── calculate_unrealized_pnl()
│   │   └── calculate_realized_pnl()
│   │
│   └── portfolio_updater.py
│       └── update_portfolio_value()
│           └── Call stored procedure: update_portfolio_value()
│
└── Database Access
    └── Uses SQLAlchemy ORM
        ├── Query orders, positions, trades
        └── Call stored procedures via text()
```

**Execution Flow**:
```
Kafka Consumer receives trading_signal
    │
    ▼
Calculate order quantity based on signal confidence
    │
    ▼
check_risk_limits()
    │
    ├─→ If FAIL: Reject order, log warning
    │
    └─→ If PASS:
        │
        ▼
create_order()
    │
    ▼
execute_order()
    │
    ├─→ Get current market price
    ├─→ Check limit order conditions
    ├─→ Update order status to FILLED
    ├─→ Create trade record
    ├─→ Update position
    ├─→ Update account cash
    └─→ Call update_portfolio_value() stored procedure
```

### Backtesting Service Components

```
Backtesting Service
│
├── main.py (Entry Point)
│   ├── FastAPI App
│   └── API Endpoints
│
├── Data Loading
│   └── historical_data_loader.py
│       └── load_historical_data(symbol, start_date, end_date)
│           └── SQLAlchemy Query → PostgreSQL
│
├── Strategy Simulator
│   ├── strategy_engine.py
│   │   └── simulate_strategy(data, strategy_func)
│   │       ├── Loop through historical data
│   │       ├── Call strategy function at each point
│   │       ├── Execute simulated trades
│   │       └── Track equity curve
│   │
│   └── strategies/
│       ├── momentum_strategy.py
│       │   └── simple_momentum_strategy(data, current_idx)
│       │       └── Moving average crossover
│       │
│       └── mean_reversion_strategy.py
│           └── mean_reversion_strategy(data, current_idx)
│               └── Buy low, sell high
│
├── Performance Calculator
│   ├── metrics_calculator.py
│   │   ├── calculate_total_return(equity_curve)
│   │   ├── calculate_sharpe_ratio(returns)
│   │   ├── calculate_max_drawdown(equity_curve)
│   │   └── calculate_win_rate(trades)
│   │
│   └── trade_analyzer.py
│       └── analyze_trades(trades)
│           ├── Count winning/losing trades
│           └── Calculate average win/loss
│
└── Report Generator
    └── report_generator.py
        └── generate_report(results)
            └── Format backtest results
```

**Backtesting Flow**:
```
API Request: POST /backtest
    │
    ▼
Load historical data from PostgreSQL
    │
    ▼
Initialize simulation:
    - capital = initial_capital
    - cash = initial_capital
    - positions = {}
    - trades = []
    - equity_curve = [initial_capital]
    │
    ▼
For each data point in history:
    │
    ├─→ Call strategy function
    │   └─→ Returns: action (BUY/SELL/HOLD), quantity
    │
    ├─→ If BUY:
    │   ├─→ Check if enough cash
    │   ├─→ Deduct cash
    │   ├─→ Add to positions
    │   └─→ Record trade
    │
    ├─→ If SELL:
    │   ├─→ Check if enough position
    │   ├─→ Add cash
    │   ├─→ Remove from positions
    │   └─→ Record trade
    │
    └─→ Calculate current portfolio value
        └─→ Append to equity_curve
    │
    ▼
Calculate performance metrics:
    ├─→ Total return
    ├─→ Sharpe ratio
    ├─→ Max drawdown
    ├─→ Win rate
    └─→ Average win/loss
    │
    ▼
Return BacktestResult
```

## Database Component Details

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

Logic:
1. Get current cash from account table
2. If BUY:
   - Calculate required cash = quantity * price
   - Return (cash >= required_cash)
3. If SELL:
   - Get current position quantity
   - Return (position_quantity >= quantity)
```

#### update_portfolio_value
```sql
FUNCTION update_portfolio_value() RETURNS TRIGGER

Triggered: Automatically when positions table changes

Logic:
1. Calculate total positions value:
   SELECT SUM(quantity * current_price) FROM positions
2. Get cash from account
3. Calculate total_value = cash + positions_value
4. Update account.total_value
5. Insert portfolio snapshot with:
   - total_value
   - cash
   - total_pnl = total_value - initial_capital
   - total_return = (total_value - initial_capital) / initial_capital
```

#### calculate_position_pnl
```sql
FUNCTION calculate_position_pnl(p_symbol VARCHAR) RETURNS VOID

Logic:
1. Get position for symbol
2. Calculate unrealized_pnl = (current_price - average_price) * quantity
3. Update position.unrealized_pnl
```

#### get_portfolio_stats
```sql
FUNCTION get_portfolio_stats(
    p_start_date TIMESTAMP,
    p_end_date TIMESTAMP
) RETURNS TABLE (
    total_return FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown FLOAT,
    volatility FLOAT
)

Logic:
1. Get all portfolio snapshots in date range
2. Extract returns array
3. Calculate:
   - Mean return
   - Standard deviation
   - Sharpe ratio = (mean_return * 252) / (std_return * sqrt(252))
   - Max drawdown from equity curve
4. Return metrics
```

### Database Triggers

#### trigger_update_portfolio_value
```sql
Trigger: AFTER INSERT OR UPDATE OR DELETE ON positions
Action: Calls update_portfolio_value() function

Purpose: Automatically update portfolio value when positions change
```

#### trigger_validate_order
```sql
Trigger: BEFORE INSERT ON orders
Action: Calls validate_order() function

Purpose: Validate order before insertion
- Check quantity > 0
- Check limit orders have price
```

## Message Queue Component Details

### Kafka Producer (Data Ingestion)

```python
class KafkaProducerClient:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',  # Wait for all replicas
            retries=3
        )
    
    def send(self, topic, value, key=None):
        # Serialize message
        # Send to Kafka broker
        # Wait for acknowledgment
```

### Kafka Consumer (ML Service)

```python
class KafkaConsumerClient:
    def __init__(self, topics, group_id):
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=['kafka:9092'],
            group_id=group_id,  # Consumer group
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest'  # Start from latest
        )
    
    def consume(self, callback):
        # Poll for messages
        # Deserialize message
        # Call callback function
```

## API Request Flow Details

### External API Calls (Market Data)

```
┌─────────────────────────────────────────┐
│  Data Ingestion Service                 │
│  (Internal, Background Job)             │
└──────────────┬──────────────────────────┘
               │
               │ Python schedule library
               │ Runs every 1 minute
               │
               ▼
┌─────────────────────────────────────────┐
│  process_and_store_market_data()        │
└──────────────┬──────────────────────────┘
               │
               │ yfinance library
               │ ticker.history()
               │
               ▼
┌─────────────────────────────────────────┐
│  yfinance API (External)                │
│  https://query1.finance.yahoo.com/...  │
└──────────────┬──────────────────────────┘
               │
               │ HTTP GET Response
               │ JSON/CSV data
               │
               ▼
┌─────────────────────────────────────────┐
│  Normalize & Process                    │
└──────────────┬──────────────────────────┘
               │
               ├─→ PostgreSQL (Store)
               └─→ Kafka (Publish)
```

### REST API Calls (Service Communication)

```
┌─────────────────────────────────────────┐
│  External Client / Developer            │
│  (Optional - for manual operations)     │
└──────────────┬──────────────────────────┘
               │
               │ HTTP POST /orders
               │
               ▼
┌─────────────────────────────────────────┐
│  Trading Service API                    │
│  http://localhost:8000                 │
└──────────────┬──────────────────────────┘
               │
               │ Validate request
               │ Check risk limits
               │
               ▼
┌─────────────────────────────────────────┐
│  Execute Order                          │
│  - Update database                      │
│  - Return response                      │
└─────────────────────────────────────────┘
```

## Summary

- **Data Ingestion**: Self-scheduled background job that fetches from external APIs
- **ML Service**: Consumes market data, generates signals, publishes to Kafka
- **Trading Service**: Consumes signals, executes trades, manages portfolio
- **Backtesting**: Reads historical data, simulates strategies, calculates metrics
- **Database**: Stores all data, provides stored procedures for complex operations
- **Kafka**: Enables async communication between services

