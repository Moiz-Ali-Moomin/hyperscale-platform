"""
Dead Letter Queue (DLQ) Handler
Processes failed events from the DLQ topic
"""

import json
import logging
from typing import Dict, Any
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DLQHandler:
    def __init__(self, bootstrap_servers: str, dlq_topic: str, retry_topic: str):
        """Initialize DLQ handler"""
        self.dlq_topic = dlq_topic
        self.retry_topic = retry_topic
        
        # Consumer for DLQ
        self.consumer = KafkaConsumer(
            dlq_topic,
            bootstrap_servers=bootstrap_servers.split(','),
            group_id='dlq-handler',
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            enable_auto_commit=False,
            auto_offset_reset='earliest',
        )
        
        # Producer for retry topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            enable_idempotence=True,
            acks='all',
        )
        
        logger.info(f"DLQ Handler initialized - DLQ: {dlq_topic}, Retry: {retry_topic}")
    
    def analyze_failure(self, event: Dict[str, Any]) -> str:
        """
        Analyze why event failed
        
        Returns:
            str: Action to take ('retry', 'discard', 'manual')
        """
        retry_count = event.get('_retry_count', 0)
        error_type = event.get('_error_type', 'unknown')
        
        # Retry logic
        if retry_count < 3 and error_type in ['transient', 'timeout']:
            return 'retry'
        elif error_type == 'validation':
            return 'discard'
        else:
            return 'manual'
    
    def process_dlq(self):
        """Process DLQ messages"""
        logger.info("Processing DLQ...")
        
        for message in self.consumer:
            event = message.value
            action = self.analyze_failure(event)
            
            if action == 'retry':
                # Increment retry count and send to retry topic
                event['_retry_count'] = event.get('_retry_count', 0) + 1
                self.producer.send(self.retry_topic, value=event)
                logger.info(f"Event sent to retry topic - Retry: {event['_retry_count']}")
                
            elif action == 'discard':
                # Log and discard
                logger.warning(f"Event discarded - Reason: validation error")
                
            else:
                # Requires manual intervention
                logger.error(f"Event requires manual review - Error: {event.get('_error_type')}")
            
            # Commit offset
            self.consumer.commit()
    
    def close(self):
        """Close connections"""
        self.consumer.close()
        self.producer.close()


if __name__ == "__main__":
    handler = DLQHandler(
        bootstrap_servers="kafka-broker-1:9092",
        dlq_topic="user-events-dlq",
        retry_topic="user-events-retry"
    )
    
    handler.process_dlq()
