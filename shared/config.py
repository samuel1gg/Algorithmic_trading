"""Configuration management for all services."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "algo_trader"
    postgres_password: str = "secure_password_123"
    postgres_db: str = "algo_trading"
    
    @property
    def postgres_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_market_data: str = "market_data"
    kafka_topic_trading_signals: str = "trading_signals"
    kafka_topic_anomalies: str = "anomalies"
    
    # Alpaca API
    alpaca_api_key: Optional[str] = None
    alpaca_secret_key: Optional[str] = None
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    
    # Trading Configuration
    initial_capital: float = 100000.0
    max_position_size: float = 0.1  # 10% of portfolio
    stop_loss_percentage: float = 0.02  # 2%
    take_profit_percentage: float = 0.05  # 5%
    min_confidence_threshold: float = 0.7
    
    # ML Configuration
    model_update_interval_hours: int = 24
    anomaly_detection_threshold: float = 0.1
    prediction_window: int = 60  # minutes
    lstm_sequence_length: int = 30
    
    # Service Ports
    trading_service_port: int = 8000
    ml_service_port: int = 8001
    data_ingestion_port: int = 8002
    backtesting_service_port: int = 8003
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

