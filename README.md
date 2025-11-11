# Algorithmic Trading Platform with Anomaly Detection

A production-grade, real-time algorithmic trading platform that integrates machine learning, real-time data processing, and advanced database operations for automated trading with anomaly detection capabilities.

## Architecture Overview

The platform is built using a microservices architecture with the following components:

- **Data Ingestion Service**: Real-time market data ingestion using Kafka
- **ML Service**: Price prediction (LSTM) and anomaly detection models
- **Trading Service**: Order execution, portfolio management, and risk management
- **Backtesting Service**: Historical strategy testing and performance analysis
- **Database**: PostgreSQL with time-series optimizations, stored procedures, and triggers
- **Monitoring**: Prometheus metrics and Grafana dashboards

## Technology Stack

- **Languages**: Python 3.11+
- **Message Queue**: Apache Kafka
- **Database**: PostgreSQL 15+ (with TimescaleDB extension for time-series)
- **ML Framework**: TensorFlow/Keras, scikit-learn
- **API Framework**: FastAPI
- **Monitoring**: Prometheus, Grafana
- **Containerization**: Docker, Docker Compose
- **Data Processing**: Pandas, NumPy

## Project Structure

```
algo_trading/
├── services/
│   ├── data-ingestion/      # Real-time data ingestion service
│   ├── ml-service/          # ML models and predictions
│   ├── trading-service/     # Trading logic and execution
│   └── backtesting-service/ # Backtesting engine
├── shared/                   # Shared utilities and models
├── database/                 # Database migrations and schemas
├── monitoring/               # Prometheus and Grafana configs
├── docker-compose.yml        # Full stack deployment
└── requirements.txt          # Python dependencies
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- 8GB+ RAM recommended

### Deployment

1. **Clone and navigate to the project**:
   ```bash
   cd algo_trading
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Initialize database**:
   ```bash
   docker-compose exec trading-service python -m database.migrations.init_db
   ```

5. **Access services**:
   - Trading API: http://localhost:8000
   - ML Service API: http://localhost:8001
   - Data Ingestion API: http://localhost:8002
   - Backtesting API: http://localhost:8003
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090

## Configuration

Key configuration options in `.env`:

- `ALPACA_API_KEY`: Alpaca API key for market data
- `ALPACA_SECRET_KEY`: Alpaca secret key
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker addresses
- `POSTGRES_URL`: Database connection string
- `INITIAL_CAPITAL`: Starting capital for trading (default: 100000)

## Features

### Real-Time Data Processing
- Kafka-based streaming pipeline for market data
- High-frequency data ingestion and processing
- Real-time feature engineering

### Machine Learning
- LSTM-based price prediction models
- Unsupervised anomaly detection (Isolation Forest)
- Model versioning and retraining pipelines

### Trading Engine
- Automated order execution
- Portfolio management with ACID transactions
- Risk management rules (position limits, stop-loss)
- Real-time P&L tracking

### Backtesting
- Historical strategy testing
- Performance metrics (Sharpe ratio, max drawdown, etc.)
- Walk-forward analysis

### Database Features
- Time-series optimized storage
- Stored procedures for complex queries
- Database triggers for business logic
- Transaction management for consistency

## API Documentation

Once services are running, access interactive API docs:
- Trading Service: http://localhost:8000/docs
- ML Service: http://localhost:8001/docs
- Data Ingestion: http://localhost:8002/docs
- Backtesting: http://localhost:8003/docs

## Monitoring

- **Grafana Dashboards**: Pre-configured dashboards for trading metrics, ML model performance, and system health
- **Prometheus Metrics**: Custom metrics for trades, predictions, anomalies, and system performance

## Development

### Running Services Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run individual services
cd services/trading-service
uvicorn main:app --reload --port 8000
```

### Database Migrations

```bash
docker-compose exec trading-service python -m database.migrations.init_db
```

### Testing

```bash
pytest tests/
```

## Production Considerations

- Use environment-specific configuration files
- Set up proper secrets management (Vault, AWS Secrets Manager)
- Implement proper logging and alerting
- Use managed Kafka (Confluent Cloud, AWS MSK)
- Consider using TimescaleDB for better time-series performance
- Implement circuit breakers and retry logic
- Set up CI/CD pipelines
- Use Kubernetes for orchestration in production

## License

MIT License

## Disclaimer

This is a simulation platform for educational purposes. Do not use with real money without proper testing and risk management.

