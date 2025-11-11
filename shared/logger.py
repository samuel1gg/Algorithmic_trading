"""Logging configuration."""
import logging
import sys
from pythonjsonlogger import jsonlogger
from shared.config import settings


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with JSON formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    handler = logging.StreamHandler(sys.stdout)
    
    if settings.log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

