.PHONY: help build up down logs clean init-db test

help:
	@echo "Available commands:"
	@echo "  make build      - Build all Docker images"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs from all services"
	@echo "  make init-db    - Initialize database schema"
	@echo "  make clean      - Remove all containers and volumes"
	@echo "  make test       - Run tests"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

init-db:
	docker-compose exec trading-service python -m database.migrations.init_db

clean:
	docker-compose down -v
	docker system prune -f

test:
	pytest tests/ -v

