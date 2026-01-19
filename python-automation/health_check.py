"""
Website Health Check Script
Monitors endpoints and sends alerts
"""

import requests
import logging
import time
from typing import Dict, List
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self, endpoints: List[Dict[str, str]]):
        """
        Initialize health checker
        
        Args:
            endpoints: List of endpoints to monitor
                       [{"name": "API", "url": "https://api.example.com/health"}]
        """
        self.endpoints = endpoints
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HyperScale-HealthCheck/1.0'
        })
    
    def check_endpoint(self, endpoint: Dict[str, str]) -> Dict:
        """
        Check single endpoint health
        
        Returns:
            dict: Health check result
        """
        name = endpoint['name']
        url = endpoint['url']
        timeout = endpoint.get('timeout', 10)
        expected_status = endpoint.get('expected_status', 200)
        
        start_time = time.time()
        
        try:
            response = self.session.get(url, timeout=timeout)
            response_time = time.time() - start_time
            
            is_healthy = response.status_code == expected_status
            
            result = {
                'name': name,
                'url': url,
                'healthy': is_healthy,
                'status_code': response.status_code,
                'response_time': round(response_time * 1000, 2),  # ms
                'timestamp': datetime.utcnow().isoformat(),
                'error': None
            }
            
            if is_healthy:
                logger.info(
                    f"✓ {name} is healthy - "
                    f"Status: {response.status_code}, "
                    f"Response Time: {result['response_time']}ms"
                )
            else:
                logger.warning(
                    f"✗ {name} returned unexpected status - "
                    f"Expected: {expected_status}, Got: {response.status_code}"
                )
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"✗ {name} timed out after {timeout}s")
            return {
                'name': name,
                'url': url,
                'healthy': False,
                'error': 'Timeout',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except requests.exceptions.ConnectionError:
            logger.error(f"✗ {name} connection failed")
            return {
                'name': name,
                'url': url,
                'healthy': False,
                'error': 'Connection Error',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"✗ {name} check failed: {e}")
            return {
                'name': name,
                'url': url,
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def check_all(self) -> List[Dict]:
        """Check all endpoints"""
        logger.info(f"Checking {len(self.endpoints)} endpoints...")
        results = []
        
        for endpoint in self.endpoints:
            result = self.check_endpoint(endpoint)
            results.append(result)
        
        # Summary
        healthy_count = sum(1 for r in results if r['healthy'])
        logger.info(
            f"Health check complete - "
            f"{healthy_count}/{len(results)} endpoints healthy"
        )
        
        return results
    
    def monitor(self, interval: int = 60):
        """Continuously monitor endpoints"""
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        
        while True:
            self.check_all()
            time.sleep(interval)


# Example usage
if __name__ == "__main__":
    endpoints = [
        {
            "name": "API Health",
            "url": "https://api.hyperscale.example.com/health",
            "timeout": 5,
            "expected_status": 200
        },
        {
            "name": "API Ready",
            "url": "https://api.hyperscale.example.com/ready",
            "timeout": 5,
            "expected_status": 200
        },
        {
            "name": "CloudFront",
            "url": "https://cdn.hyperscale.example.com",
            "timeout": 10,
            "expected_status": 200
        }
    ]
    
    checker = HealthChecker(endpoints)
    checker.check_all()
