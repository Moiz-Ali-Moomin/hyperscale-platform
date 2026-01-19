"""
Kafka Event Producer
Publishes user events to Kafka with idempotent writes
"""

import json
import logging
from typing import Dict, Any
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventProducer:
    def __init__(self, bootstrap_servers: str, topic: str):
        """Initialize Kafka producer with best practices"""
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(','),
            # Serialization
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            # Idempotence for exactly-once semantics
            enable_idempotence=True,
            # Reliability
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=5,
            # Performance
            compression_type='lz4',
            batch_size=16384,
            linger_ms=10,
            buffer_memory=33554432,
            # Timeout
            request_timeout_ms=30000,
        )
        logger.info(f"Producer initialized for topic: {self.topic}")
    
    def send_event(self, event_data: Dict[str, Any], key: str = None) -> bool:
        """
        Send event to Kafka
        
        Args:
            event_data: Event payload dictionary
            key: Optional partition key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add metadata
            event_data['_producer'] = 'hyperscale-api'
            event_data['_version'] = '1.0'
            
            # Send with callback
            future = self.producer.send(
                topic=self.topic,
                key=key,
                value=event_data
            )
            
            # Wait for result (synchronous for demonstration)
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Event sent - Topic: {record_metadata.topic}, "
                f"Partition: {record_metadata.partition}, "
                f"Offset: {record_metadata.offset}"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to send event: {e}")
            return False
    
    def send_batch(self, events: list) -> None:
        """Send multiple events asynchronously"""
        futures = []
        for event in events:
            key = event.get('user_id')
            future = self.producer.send(
                topic=self.topic,
                key=key,
                value=event
            )
            futures.append(future)
        
        # Ensure all messages are sent
        self.producer.flush()
        
        # Check results
        success = 0
        failed = 0
        for future in futures:
            try:
                future.get(timeout=10)
                success += 1
            except KafkaError:
                failed += 1
        
        logger.info(f"Batch sent - Success: {success}, Failed: {failed}")
    
    def close(self):
        """Close producer gracefully"""
        logger.info("Closing producer...")
        self.producer.close()


# Example usage
if __name__ == "__main__":
    producer = EventProducer(
        bootstrap_servers="kafka-broker-1:9092,kafka-broker-2:9092",
        topic="user-events"
    )
    
    # Send single event
    event = {
        "user_id": "user123",
        "event_type": "purchase",
        "product_id": "prod456",
        "amount": 99.99,
        "timestamp": "2024-01-20T10:30:00Z"
    }
    
    producer.send_event(event, key="user123")
    producer.close()
