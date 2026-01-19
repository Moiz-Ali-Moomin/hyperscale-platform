"""
Database Metrics Collector
Extracts purchase metrics from MySQL database
"""

import mysql.connector
import logging
from datetime import datetime, timedelta
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DBMetricsCollector:
    def __init__(self, host: str, user: str, password: str, database: str):
        """Initialize database connection"""
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'autocommit': True
        }
        logger.info(f"Initialized DB collector for {database}@{host}")
    
    def get_connection(self):
        """Create database connection"""
        return mysql.connector.connect(**self.config)
    
    def get_purchase_count(self, hours: int = 24) -> int:
        """Get purchase count for last N hours"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT COUNT(*) as purchase_count
            FROM purchases
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
        """
        
        cursor.execute(query, (hours,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result[0] if result else 0
    
    def get_revenue(self, hours: int = 24) -> float:
        """Get total revenue for last N hours"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT COALESCE(SUM(amount), 0) as total_revenue
            FROM purchases
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            AND status = 'completed'
        """
        
        cursor.execute(query, (hours,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return float(result[0]) if result else 0.0
    
    def get_top_products(self, limit: int = 10) -> List[Dict]:
        """Get top selling products"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                product_id,
                product_name,
                COUNT(*) as purchase_count,
                SUM(amount) as total_revenue
            FROM purchases
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY product_id, product_name
            ORDER BY purchase_count DESC
            LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results
    
    def get_user_activity(self) -> Dict:
        """Get user activity metrics"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        queries = {
            'active_users_24h': """
                SELECT COUNT(DISTINCT user_id) as count
                FROM user_activity
                WHERE last_activity >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """,
            'new_users_24h': """
                SELECT COUNT(*) as count
                FROM users
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """,
            'avg_session_duration': """
                SELECT AVG(TIMESTAMPDIFF(MINUTE, session_start, session_end)) as avg_minutes
                FROM user_sessions
                WHERE session_start >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
        }
        
        results = {}
        for metric, query in queries.items():
            cursor.execute(query)
            result = cursor.fetchone()
            results[metric] = result['count'] if 'count' in result else result.get('avg_minutes', 0)
        
        cursor.close()
        conn.close()
        
        return results
    
    def generate_report(self) -> Dict:
        """Generate comprehensive metrics report"""
        logger.info("Generating database metrics report...")
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'purchases': {
                'count_24h': self.get_purchase_count(24),
                'count_1h': self.get_purchase_count(1),
                'revenue_24h': self.get_revenue(24),
                'revenue_1h': self.get_revenue(1)
            },
            'top_products': self.get_top_products(10),
            'user_activity': self.get_user_activity()
        }
        
        logger.info(f"Report generated - Purchases (24h): {report['purchases']['count_24h']}")
        logger.info(f"Revenue (24h): ${report['purchases']['revenue_24h']:.2f}")
        
        return report


if __name__ == "__main__":
    # Example usage
    collector = DBMetricsCollector(
        host="mysql-primary.example.com",
        user="readonly_user",
        password="secure_password",
        database="hyperscale"
    )
    
    report = collector.generate_report()
    
    print("\n" + "=" * 60)
    print("DATABASE METRICS REPORT")
    print("=" * 60)
    print(f"\nTimestamp: {report['timestamp']}\n")
    
    print("PURCHASES:")
    print(f"  Last 24 hours: {report['purchases']['count_24h']}")
    print(f"  Last 1 hour: {report['purchases']['count_1h']}")
    print(f"  Revenue (24h): ${report['purchases']['revenue_24h']:,.2f}")
    print(f"  Revenue (1h): ${report['purchases']['revenue_1h']:,.2f}\n")
    
    print("USER ACTIVITY:")
    print(f"  Active users (24h): {report['user_activity']['active_users_24h']}")
    print(f"  New users (24h): {report['user_activity']['new_users_24h']}")
    print(f"  Avg session duration: {report['user_activity']['avg_session_duration']:.1f} min\n")
    
    print("TOP PRODUCTS:")
    for i, product in enumerate(report['top_products'], 1):
        print(f"  {i}. {product['product_name']}: {product['purchase_count']} sales, "
              f"${product['total_revenue']:,.2f}")
