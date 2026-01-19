"""
Kafka Event Consumer
Processes user events from Kafka with manual offset management
"""

import json
import logging
import signal
import sys
from typing import Dict, Any
from kafka import KafkaConsumer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventConsumer:
    def __init__(self, bootstrap_servers: str, topic: str, group_id: str):
        """Initialize Kafka consumer with best practices"""
        self.topic = topic
        self.running = True
        
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers.split(','),
            # Consumer group
            group_id=group_id,
            # Deserialization
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            # Offset management
            enable_auto_commit=False,
            auto_offset_reset='earliest',
            # Performance
            fetch_min_bytes=1024,
            fetch_max_wait_ms=500,
            max_poll_records=500,
            max_poll_interval_ms=300000,
            # Session management
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
        )
        
        logger.info(f"Consumer initialized - Topic: {self.topic}, Group: {group_id}")
        
        # Handle shutdown gracefully
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def process_event(self, event: Dict[str, Any]) -> bool:
        """
        Process a single event
        
        Args:
            event: Event data dictionary
            
        Returns:
            bool: True if processing successful
        """
        try:
            # Simulate event processing
            event_type = event.get('event_type')
            user_id = event.get('user_id')
            
            logger.info(f"Processing {event_type} for user {user_id}")
            
            # Add your business logic here
            # e.g., save to database, trigger workflows, etc.
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return False
    
    def consume(self):
        """Main consumer loop"""
        logger.info("Starting consumer...")
        
        try:
            while self.running:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                if not message_batch:
                    continue
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        # Process event
                        success = self.process_event(message.value)
                        
                        if success:
                            # Commit offset after successful processing
                            self.consumer.commit()
                            logger.debug(
                                f"Processed and committed - "
                                f"Partition: {message.partition}, "
                                f"Offset: {message.offset}"
                            )
                        else:
                            # Send to DLQ (Dead Letter Queue)
                            logger.error(
                                f"Failed to process message - "
                                f"Partition: {message.partition}, "
                                f"Offset: {message.offset}"
                            )
                            # In production, send to DLQ topic here
                            
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        
        finally:
            self.close()
    
    def shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        logger.info("Shutdown signal received...")
        self.running = False
    
    def close(self):
        """Close consumer gracefully"""
        logger.info("Closing consumer...")
        self.consumer.close()


# Example usage
if __name__ == "__main__":
    consumer = EventConsumer(
        bootstrap_servers="kafka-broker-1:9092,kafka-broker-2:9092",
        topic="user-events",
        group_id="hyperscale-consumer-group"
    )
    
    consumer.consume()
