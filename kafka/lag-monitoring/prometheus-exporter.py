"""
Kafka Consumer Lag Monitoring
Exports consumer lag metrics for Prometheus
"""

import logging
import time
from kafka import KafkaAdminClient, KafkaConsumer
from kafka.structs import TopicPartition
from prometheus_client import start_http_server, Gauge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
consumer_lag_gauge = Gauge(
    'kafka_consumer_lag',
    'Consumer lag per topic/partition/group',
    ['topic', 'partition', 'consumer_group']
)

consumer_offset_gauge = Gauge(
    'kafka_consumer_offset',
    'Consumer current offset',
    ['topic', 'partition', 'consumer_group']
)

partition_end_offset_gauge = Gauge(
    'kafka_partition_end_offset',
    'Partition end offset',
    ['topic', 'partition']
)


class LagMonitor:
    def __init__(self, bootstrap_servers: str, consumer_groups: list):
        """Initialize lag monitor"""
        self.bootstrap_servers = bootstrap_servers
        self.consumer_groups = consumer_groups
        
        # Admin client for metadata
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers.split(',')
        )
        
        logger.info(f"Lag Monitor initialized for groups: {consumer_groups}")
    
    def get_consumer_lag(self, group_id: str, topic: str):
        """Calculate consumer lag for a group"""
        consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers.split(','),
            group_id=group_id,
            enable_auto_commit=False
        )
        
        # Get topic partitions
        partitions = consumer.partitions_for_topic(topic)
        if not partitions:
            logger.warning(f"No partitions found for topic: {topic}")
            return
        
        topic_partitions = [
            TopicPartition(topic, p) for p in partitions
        ]
        
        # Get committed offsets
        committed = consumer.committed_offsets(topic_partitions)
        
        # Get end offsets (latest)
        end_offsets = consumer.end_offsets(topic_partitions)
        
        # Calculate and export lag
        for tp in topic_partitions:
            committed_offset = committed.get(tp, 0)
            end_offset = end_offsets.get(tp, 0)
            lag = end_offset - committed_offset
            
            # Export to Prometheus
            consumer_lag_gauge.labels(
                topic=topic,
                partition=tp.partition,
                consumer_group=group_id
            ).set(lag)
            
            consumer_offset_gauge.labels(
                topic=topic,
                partition=tp.partition,
                consumer_group=group_id
            ).set(committed_offset)
            
            partition_end_offset_gauge.labels(
                topic=topic,
                partition=tp.partition
            ).set(end_offset)
            
            logger.debug(
                f"Group: {group_id}, Topic: {topic}, "
                f"Partition: {tp.partition}, Lag: {lag}"
            )
        
        consumer.close()
    
    def monitor(self, interval: int = 30):
        """Continuously monitor lag"""
        logger.info(f"Starting lag monitoring (interval: {interval}s)")
        
        while True:
            try:
                for group_id in self.consumer_groups:
                    # Monitor user-events topic
                    self.get_consumer_lag(group_id, 'user-events')
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(interval)


if __name__ == "__main__":
    # Start Prometheus HTTP server
    start_http_server(9090)
    logger.info("Prometheus exporter started on :9090")
    
    # Start monitoring
    monitor = LagMonitor(
        bootstrap_servers="kafka-broker-1:9092,kafka-broker-2:9092",
        consumer_groups=['hyperscale-consumer-group']
    )
    
    monitor.monitor(interval=30)
