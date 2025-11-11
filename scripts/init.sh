#!/bin/bash

# Initialization script for the trading platform

set -e

echo "🚀 Initializing Algorithmic Trading Platform..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env file created. Please edit it with your configuration."
    else
        echo "⚠️  .env.example not found. Creating basic .env file..."
        cat > .env << EOF
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=algo_trader
POSTGRES_PASSWORD=secure_password_123
POSTGRES_DB=algo_trading
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
INITIAL_CAPITAL=100000.0
EOF
    fi
fi

# Build Docker images
echo "🔨 Building Docker images..."
docker-compose build

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
timeout=60
counter=0
until docker-compose exec -T postgres pg_isready -U algo_trader > /dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        echo "❌ PostgreSQL failed to start within $timeout seconds"
        exit 1
    fi
done
echo "✅ PostgreSQL is ready"

# Wait for Kafka to be ready
echo "⏳ Waiting for Kafka to be ready..."
timeout=60
counter=0
until docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        echo "❌ Kafka failed to start within $timeout seconds"
        exit 1
    fi
done
echo "✅ Kafka is ready"

# Initialize database
echo "🗄️  Initializing database..."
sleep 5  # Give services time to start
docker-compose exec -T trading-service python -m database.migrations.init_db || {
    echo "⚠️  Database initialization failed. Trying again..."
    sleep 10
    docker-compose exec -T trading-service python -m database.migrations.init_db
}

echo ""
echo "✅ Initialization complete!"
echo ""
echo "📊 Service URLs:"
echo "   Trading Service:  http://localhost:8000/docs"
echo "   ML Service:       http://localhost:8001/docs"
echo "   Data Ingestion:   http://localhost:8002/docs"
echo "   Backtesting:      http://localhost:8003/docs"
echo "   Grafana:          http://localhost:3000 (admin/admin)"
echo "   Prometheus:       http://localhost:9090"
echo ""
echo "📝 Next steps:"
echo "   1. Check service logs: docker-compose logs -f"
echo "   2. Monitor services: docker-compose ps"
echo "   3. View data ingestion: docker-compose logs data-ingestion"
echo ""

