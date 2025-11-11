# Quick Start Guide

Get the Algorithmic Trading Platform up and running in minutes!

## Prerequisites

- Docker Desktop installed and running
- 8GB+ RAM available
- Terminal/Command Line access

## Step 1: Clone and Navigate

```bash
cd algo_trading
```

## Step 2: Initialize (Automated)

Run the initialization script:

```bash
./scripts/init.sh
```

This will:
- Create `.env` file if it doesn't exist
- Build all Docker images
- Start all services
- Initialize the database
- Wait for services to be ready

## Step 3: Verify Services

Check that all services are running:

```bash
docker-compose ps
```

You should see all services with "Up" status.

## Step 4: Access Services

Open your browser and visit:

- **Trading API**: http://localhost:8000/docs
- **ML Service API**: http://localhost:8001/docs
- **Data Ingestion API**: http://localhost:8002/docs
- **Backtesting API**: http://localhost:8003/docs
- **Grafana Dashboard**: http://localhost:3000 (login: admin/admin)
- **Prometheus**: http://localhost:9090

## Step 5: Check Data Collection

View data ingestion logs:

```bash
docker-compose logs -f data-ingestion
```

You should see data being collected for symbols like AAPL, MSFT, GOOGL, etc.

## Step 6: View Portfolio

Check your portfolio status:

```bash
curl http://localhost:8000/portfolio
```

Or use the interactive API docs at http://localhost:8000/docs

## Step 7: Run a Backtest

Test a strategy on historical data:

```bash
curl -X POST "http://localhost:8003/backtest?symbol=AAPL&start_date=2024-01-01T00:00:00&end_date=2024-12-31T23:59:59&initial_capital=100000&strategy=momentum"
```

## Common Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f trading-service
docker-compose logs -f ml-service
```

### Stop Services
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart
```

### Rebuild After Code Changes
```bash
docker-compose build
docker-compose up -d
```

### Check Service Health
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## Troubleshooting

### Services won't start

1. Check Docker is running: `docker info`
2. Check port conflicts: Ensure ports 8000-8003, 5432, 9092, 3000, 9090 are free
3. Check logs: `docker-compose logs`

### Database connection errors

Wait a bit longer for PostgreSQL to initialize, then:

```bash
docker-compose exec postgres pg_isready -U algo_trader
```

### No trading signals

1. Ensure data ingestion is running: `docker-compose logs data-ingestion`
2. Wait for ML models to train (needs ~100 data points)
3. Check ML service logs: `docker-compose logs ml-service`

### Reset Everything

```bash
docker-compose down -v
./scripts/init.sh
```

This will remove all data and start fresh.

## Next Steps

1. **Monitor Performance**: Visit Grafana at http://localhost:3000
2. **Explore APIs**: Use the interactive docs at each service's `/docs` endpoint
3. **Customize Strategy**: Modify ML models or trading logic
4. **Add More Symbols**: Edit data ingestion service to track more stocks
5. **Read Documentation**: Check `ARCHITECTURE.md` and `DEPLOYMENT.md`

## Example API Calls

### Get Portfolio
```bash
curl http://localhost:8000/portfolio | jq
```

### Get Price Prediction
```bash
curl -X POST http://localhost:8001/predict/AAPL | jq
```

### Manually Trigger Data Ingestion
```bash
curl -X POST http://localhost:8002/ingest/AAPL
```

### Get Recent Trades
```bash
curl http://localhost:8000/trades | jq
```

## Support

For detailed information, see:
- `README.md` - Overview and features
- `ARCHITECTURE.md` - System architecture
- `DEPLOYMENT.md` - Production deployment guide

Happy Trading! 📈

