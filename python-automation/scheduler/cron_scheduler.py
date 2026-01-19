"""
Cron Scheduler for Automation Tasks
Orchestrates automated monitoring and reporting
"""

import schedule
import time
import logging
from datetime import datetime
from health_check import HealthChecker
from alb_metrics import ALBMetricsCollector
from db_metrics import DBMetricsCollector
from email_report import EmailReporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutomationScheduler:
    def __init__(self):
        """Initialize automation scheduler"""
        logger.info("Initializing automation scheduler...")
        
        # Initialize components
        self.health_checker = HealthChecker([
            {"name": "API Health", "url": "https://api.hyperscale.com/health"},
            {"name": "API Ready", "url": "https://api.hyperscale.com/ready"}
        ])
        
        self.alb_collector = ALBMetricsCollector(region='us-east-1')
        
        self.db_collector = DBMetricsCollector(
            host="mysql-primary.example.com",
            user="readonly",
            password="password",
            database="hyperscale"
        )
        
        self.email_reporter = EmailReporter(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            username="reports@hyperscale.com",
            password="app_password"
        )
        
        self.recipients = ['ops@hyperscale.com', 'management@hyperscale.com']
    
    def health_check_job(self):
        """Run health checks"""
        logger.info("Running scheduled health check...")
        try:
            self.health_checker.check_all()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def metrics_collection_job(self):
        """Collect and log metrics"""
        logger.info("Running metrics collection...")
        try:
            # Collect DB metrics
            db_metrics = self.db_collector.generate_report()
            logger.info(f"DB Metrics - Purchases: {db_metrics['purchases']['count_24h']}")
            
            # Collect ALB metrics
            alb_report = self.alb_collector.generate_report()
            logger.info("ALB metrics collected")
            
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
    
    def daily_report_job(self):
        """Send daily report"""
        logger.info("Generating and sending daily report...")
        try:
            # Collect metrics
            metrics = self.db_collector.generate_report()
            
            # Send email
            success = self.email_reporter.send_daily_report(
                recipients=self.recipients,
                metrics=metrics
            )
            
            if success:
                logger.info("Daily report sent successfully")
            else:
                logger.error("Failed to send daily report")
                
        except Exception as e:
            logger.error(f"Daily report job failed: {e}")
    
    def setup_schedule(self):
        """Configure job schedules"""
        logger.info("Setting up job schedules...")
        
        # Health checks every 5 minutes
        schedule.every(5).minutes.do(self.health_check_job)
        
        # Metrics collection every hour
        schedule.every(1).hours.do(self.metrics_collection_job)
        
        # Daily report at 8 AM
        schedule.every().day.at("08:00").do(self.daily_report_job)
        
        logger.info("Schedule configured:")
        logger.info("  - Health checks: Every 5 minutes")
        logger.info("  - Metrics collection: Every hour")
        logger.info("  - Daily report: 08:00 UTC")
    
    def run(self):
        """Start the scheduler"""
        self.setup_schedule()
        
        logger.info("Automation scheduler started")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")


if __name__ == "__main__":
    scheduler = AutomationScheduler()
    scheduler.run()
