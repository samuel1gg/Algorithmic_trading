"""Kafka producer and consumer utilities."""
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import json
import logging
from typing import Optional, Callable
from shared.config import settings

logger = logging.getLogger(__name__)


class KafkaProducerClient:
    """Kafka producer for publishing messages."""
    
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=1
        )
    
    def send(self, topic: str, value: dict, key: Optional[str] = None):
        """Send a message to a topic."""
        try:
            future = self.producer.send(topic, value=value, key=key)
            future.get(timeout=10)
            logger.debug(f"Message sent to topic {topic}")
        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            raise
    
    def close(self):
        """Close the producer."""
        self.producer.close()


class KafkaConsumerClient:
    """Kafka consumer for subscribing to topics."""
    
    def __init__(self, topics: list[str], group_id: str):
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            consumer_timeout_ms=1000
        )
        self.topics = topics
    
    def consume(self, callback: Callable[[dict, Optional[str]], None]):
        """Consume messages and call callback for each message."""
        try:
            for message in self.consumer:
                callback(message.value, message.key)
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
            raise
    
    def close(self):
        """Close the consumer."""
        self.consumer.close()

