"""
Email Report Generator
Sends automated reports via email
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailReporter:
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        """Initialize email reporter"""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        logger.info(f"Email reporter initialized - SMTP: {smtp_host}:{smtp_port}")
    
    def send_email(self, to_addresses: List[str], subject: str, 
                   body: str, attachments: List[str] = None) -> bool:
        """
        Send email with optional attachments
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Email body (HTML supported)
            attachments: List of file paths to attach
        
        Returns:
            bool: True if sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = subject
            msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
            
            # Add body
            msg.attach(MIMEText(body, 'html'))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    try:
                        with open(file_path, 'rb') as f:
                            attachment = MIMEApplication(f.read())
                            attachment.add_header(
                                'Content-Disposition',
                                'attachment',
                                filename=file_path.split('/')[-1]
                            )
                            msg.attach(attachment)
                    except Exception as e:
                        logger.warning(f"Failed to attach {file_path}: {e}")
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {', '.join(to_addresses)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def generate_html_report(self, metrics: Dict) -> str:
        """Generate HTML report from metrics"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                th {{ background-color: #3498db; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                .metric-box {{ background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .highlight {{ color: #27ae60; font-weight: bold; }}
                .warning {{ color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>HyperScale Platform - Daily Report</h1>
            <p><strong>Generated:</strong> {metrics.get('timestamp', 'N/A')}</p>
            
            <h2>📊 Purchase Metrics</h2>
            <div class="metric-box">
                <p><strong>Purchases (24h):</strong> <span class="highlight">{metrics.get('purchases', {}).get('count_24h', 0):,}</span></p>
                <p><strong>Revenue (24h):</strong> <span class="highlight">${metrics.get('purchases', {}).get('revenue_24h', 0):,.2f}</span></p>
                <p><strong>Purchases (1h):</strong> {metrics.get('purchases', {}).get('count_1h', 0):,}</p>
                <p><strong>Revenue (1h):</strong> ${metrics.get('purchases', {}).get('revenue_1h', 0):,.2f}</p>
            </div>
            
            <h2>👥 User Activity</h2>
            <div class="metric-box">
                <p><strong>Active Users (24h):</strong> {metrics.get('user_activity', {}).get('active_users_24h', 0):,}</p>
                <p><strong>New Users (24h):</strong> {metrics.get('user_activity', {}).get('new_users_24h', 0):,}</p>
                <p><strong>Avg Session Duration:</strong> {metrics.get('user_activity', {}).get('avg_session_duration', 0):.1f} minutes</p>
            </div>
            
            <h2>🏆 Top Products</h2>
            <table>
                <tr>
                    <th>#</th>
                    <th>Product</th>
                    <th>Sales</th>
                    <th>Revenue</th>
                </tr>
        """
        
        for i, product in enumerate(metrics.get('top_products', [])[:10], 1):
            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{product.get('product_name', 'N/A')}</td>
                    <td>{product.get('purchase_count', 0):,}</td>
                    <td>${product.get('total_revenue', 0):,.2f}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
                This is an automated report from the HyperScale Platform monitoring system.
            </p>
        </body>
        </html>
        """
        
        return html
    
    def send_daily_report(self, recipients: List[str], metrics: Dict) -> bool:
        """Send formatted daily report"""
        subject = f"HyperScale Platform - Daily Report - {datetime.utcnow().strftime('%Y-%m-%d')}"
        body = self.generate_html_report(metrics)
        
        return self.send_email(recipients, subject, body)


if __name__ == "__main__":
    # Example usage
    reporter = EmailReporter(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="reports@hyperscale.com",
        password="app_password"
    )
    
    # Sample metrics
    sample_metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'purchases': {
            'count_24h': 1234,
            'count_1h': 52,
            'revenue_24h': 45678.90,
            'revenue_1h': 1890.50
        },
        'user_activity': {
            'active_users_24h': 5432,
            'new_users_24h': 234,
            'avg_session_duration': 12.5
        },
        'top_products': [
            {'product_name': 'Product A', 'purchase_count': 156, 'total_revenue': 7800.00},
            {'product_name': 'Product B', 'purchase_count': 143, 'total_revenue': 7150.00}
        ]
    }
    
    reporter.send_daily_report(['team@hyperscale.com'], sample_metrics)
