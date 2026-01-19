"""
ALB Metrics Collector
Collects ALB metrics using boto3
"""

import boto3
import logging
from datetime import datetime, timedelta
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ALBMetricsCollector:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize ALB metrics collector"""
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.elbv2 = boto3.client('elbv2', region_name=region)
        self.region = region
    
    def get_load_balancers(self) -> List[Dict]:
        """Get all ALBs in the region"""
        response = self.elbv2.describe_load_balancers()
        albs = []
        
        for lb in response['LoadBalancers']:
            if lb['Type'] == 'application':
                albs.append({
                    'name': lb['LoadBalancerName'],
                    'arn': lb['LoadBalancerArn'],
                    'dns': lb['DNSName']
                })
        
        logger.info(f"Found {len(albs)} Application Load Balancers")
        return albs
    
    def get_metrics(self, lb_name: str, metric_name: str,
                    period: int = 300, hours: int = 1) -> Dict:
        """
        Get CloudWatch metrics for ALB
        
        Args:
            lb_name: Load balancer name
            metric_name: Metric to retrieve
            period: Period in seconds
            hours: Hours of data to retrieve
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Extract LB name from full ARN format
        lb_dimensions = lb_name.split('/')
        
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/ApplicationELB',
            MetricName=metric_name,
            Dimensions=[
                {
                    'Name': 'LoadBalancer',
                    'Value': f"{lb_dimensions[-3]}/{lb_dimensions[-2]}/{lb_dimensions[-1]}"
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=['Average', 'Sum', 'Maximum', 'Minimum']
        )
        
        return response['Datapoints']
    
    def collect_all_metrics(self, lb_arn: str) -> Dict:
        """Collect all important ALB metrics"""
        metrics = {
            'RequestCount': 'Requests',
            'TargetResponseTime': 'Response Time (seconds)',
            'HTTPCode_Target_2XX_Count': 'Successful Responses',
            'HTTPCode_Target_4XX_Count': 'Client Errors',
            'HTTPCode_Target_5XX_Count': 'Server Errors',
            'ActiveConnectionCount': 'Active Connections',
            'NewConnectionCount': 'New Connections',
            'ProcessedBytes': 'Processed Bytes',
            'TargetConnectionErrorCount': 'Connection Errors',
            'HealthyHostCount': 'Healthy Targets',
            'UnHealthyHostCount': 'Unhealthy Targets'
        }
        
        results = {}
        
        for metric_name, description in metrics.items():
            logger.info(f"Collecting {metric_name}...")
            datapoints = self.get_metrics(lb_arn, metric_name)
            
            if datapoints:
                latest = max(datapoints, key=lambda x: x['Timestamp'])
                results[metric_name] = {
                    'description': description,
                    'average': latest.get('Average', 0),
                    'sum': latest.get('Sum', 0),
                    'max': latest.get('Maximum', 0),
                    'min': latest.get('Minimum', 0),
                    'timestamp': latest['Timestamp'].isoformat()
                }
            else:
                results[metric_name] = {
                    'description': description,
                    'error': 'No data available'
                }
        
        return results
    
    def generate_report(self) -> str:
        """Generate ALB metrics report"""
        albs = self.get_load_balancers()
        
        report = f"ALB Metrics Report - {datetime.utcnow().isoformat()}\n"
        report += "=" * 80 + "\n\n"
        
        for alb in albs:
            report += f"Load Balancer: {alb['name']}\n"
            report += f"DNS: {alb['dns']}\n"
            report += "-" * 80 + "\n"
            
            metrics = self.collect_all_metrics(alb['arn'])
            
            for metric_name, data in metrics.items():
                if 'error' not in data:
                    report += f"{data['description']}:\n"
                    report += f"  Average: {data['average']:.2f}\n"
                    report += f"  Sum: {data['sum']:.2f}\n"
                    report += f"  Max: {data['max']:.2f}\n"
                    report += f"  Min: {data['min']:.2f}\n"
                else:
                    report += f"{data['description']}: {data['error']}\n"
            
            report += "\n"
        
        return report


if __name__ == "__main__":
    collector = ALBMetricsCollector(region='us-east-1')
    report = collector.generate_report()
    print(report)
    
    # Save to file
    with open('alb-metrics-report.txt', 'w') as f:
        f.write(report)
    
    logger.info("Report saved to alb-metrics-report.txt")
