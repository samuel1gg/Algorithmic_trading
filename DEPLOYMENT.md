# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM recommended
- 20GB+ free disk space

## Quick Start

1. **Clone and navigate to the project**:
   ```bash
   cd algo_trading
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Build and start services**:
   ```bash
   make build
   make up
   ```

4. **Initialize database**:
   ```bash
   make init-db
   ```

5. **Verify services are running**:
   ```bash
   docker-compose ps
   ```

## Service URLs

- **Trading Service API**: http://localhost:8000/docs
- **ML Service API**: http://localhost:8001/docs
- **Data Ingestion API**: http://localhost:8002/docs
- **Backtesting API**: http://localhost:8003/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## Configuration

### Environment Variables

Key variables in `.env`:

- `POSTGRES_*`: Database configuration
- `KAFKA_*`: Kafka broker configuration
- `ALPACA_*`: Alpaca API credentials (optional, for real market data)
- `INITIAL_CAPITAL`: Starting capital for trading
- `MAX_POSITION_SIZE`: Maximum position size as fraction of portfolio
- `STOP_LOSS_PERCENTAGE`: Stop loss percentage
- `TAKE_PROFIT_PERCENTAGE`: Take profit percentage

### Database Setup

The database is automatically initialized on first run. To manually initialize:

```bash
make init-db
```

This creates:
- All tables
- Stored procedures
- Database triggers
- Initial account with capital

## Monitoring

### Prometheus

Prometheus scrapes metrics from all services every 15 seconds. Access at http://localhost:9090

### Grafana

Grafana is pre-configured with:
- Prometheus data source
- Trading dashboard

Login: admin/admin (change on first login)

## Troubleshooting

### Services won't start

1. Check logs:
   ```bash
   make logs
   ```

2. Verify Docker resources:
   ```bash
   docker system df
   ```

3. Check port conflicts:
   ```bash
   netstat -an | grep -E '8000|8001|8002|8003|5432|9092|3000|9090'
   ```

### Database connection errors

1. Wait for PostgreSQL to be ready:
   ```bash
   docker-compose exec postgres pg_isready -U algo_trader
   ```

2. Check database logs:
   ```bash
   docker-compose logs postgres
   ```

### Kafka connection errors

1. Wait for Kafka to be ready:
   ```bash
   docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
   ```

2. Check Kafka logs:
   ```bash
   docker-compose logs kafka
   ```

### ML models not training

1. Ensure data ingestion is running and collecting data
2. Wait for sufficient historical data (at least 100 data points)
3. Check ML service logs:
   ```bash
   docker-compose logs ml-service
   ```

## Production Deployment

### Security Considerations

1. **Change default passwords**:
   - PostgreSQL password
   - Grafana admin password
   - All service credentials

2. **Use secrets management**:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Kubernetes Secrets

3. **Enable TLS**:
   - Database connections
   - Kafka brokers
   - API endpoints

4. **Network security**:
   - Use private networks
   - Implement firewall rules
   - Use VPN for access

### Scaling

#### Horizontal Scaling

- **Data Ingestion**: Scale based on number of symbols
- **ML Service**: Scale based on prediction load
- **Trading Service**: Usually single instance for consistency
- **Backtesting**: Scale based on concurrent backtests

#### Database Scaling

- Use read replicas for analytics
- Consider TimescaleDB for better time-series performance
- Implement connection pooling

#### Kafka Scaling

- Increase partition count for topics
- Add more Kafka brokers
- Use managed Kafka (Confluent Cloud, AWS MSK)

### High Availability

1. **Database**:
   - Use PostgreSQL replication
   - Regular backups
   - Point-in-time recovery

2. **Kafka**:
   - Multi-broker setup
   - Replication factor > 1
   - Use managed Kafka service

3. **Services**:
   - Deploy multiple instances
   - Use load balancer
   - Implement health checks

### Monitoring in Production

1. **Set up alerting**:
   - Prometheus Alertmanager
   - PagerDuty integration
   - Email/Slack notifications

2. **Log aggregation**:
   - ELK Stack
   - Splunk
   - CloudWatch Logs

3. **APM**:
   - New Relic
   - Datadog
   - Application Insights

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U algo_trader algo_trading > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U algo_trader algo_trading < backup.sql
```

### Regular Backups

Set up cron job for automated backups:

```bash
0 2 * * * docker-compose exec postgres pg_dump -U algo_trader algo_trading > /backups/backup_$(date +\%Y\%m\%d).sql
```

## Performance Tuning

### Database

- Increase `shared_buffers`
- Tune `work_mem`
- Add indexes for frequently queried columns
- Use connection pooling (PgBouncer)

### Kafka

- Tune `batch.size` and `linger.ms`
- Adjust `num.partitions`
- Configure retention policies

### Python Services

- Use async/await for I/O operations
- Implement connection pooling
- Use caching (Redis) for frequently accessed data
- Optimize database queries

## Maintenance

### Regular Tasks

1. **Monitor disk space**
2. **Review logs for errors**
3. **Update dependencies**
4. **Retrain ML models**
5. **Review and optimize queries**
6. **Clean up old data**

### Model Retraining

Models should be retrained regularly:

```bash
# Trigger retraining
curl -X POST http://localhost:8001/retrain
```

Or set up scheduled retraining via cron or Kubernetes CronJob.

