import time
import psutil
import threading
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os

class PerformanceMonitor:
    """Performance monitoring utility for tracking application metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
        self.monitoring_active = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start background performance monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Store metrics
                timestamp = datetime.now().isoformat()
                self.metrics[timestamp] = {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_mb': memory.used / (1024 * 1024),
                    'disk_percent': disk.percent,
                    'disk_free_gb': disk.free / (1024 * 1024 * 1024)
                }
                
                # Keep only last 1000 entries
                if len(self.metrics) > 1000:
                    oldest_key = min(self.metrics.keys())
                    del self.metrics[oldest_key]
                    
            except Exception as e:
                print(f"Performance monitoring error: {e}")
            
            time.sleep(5)  # Collect metrics every 5 seconds
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_mb': round(memory.used / (1024 * 1024), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024 * 1024 * 1024), 2),
                'uptime_seconds': time.time() - self.start_time
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_average_metrics(self, minutes: int = 5) -> Dict[str, Any]:
        """Get average metrics over specified time period"""
        if not self.metrics:
            return {}
        
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        recent_metrics = {
            k: v for k, v in self.metrics.items() 
            if datetime.fromisoformat(k).timestamp() > cutoff_time
        }
        
        if not recent_metrics:
            return {}
        
        # Calculate averages
        cpu_values = [m['cpu_percent'] for m in recent_metrics.values()]
        memory_values = [m['memory_percent'] for m in recent_metrics.values()]
        
        return {
            'avg_cpu_percent': round(sum(cpu_values) / len(cpu_values), 2),
            'avg_memory_percent': round(sum(memory_values) / len(memory_values), 2),
            'sample_count': len(recent_metrics)
        }
    
    def save_metrics_report(self, filename: str = None):
        """Save metrics to JSON file"""
        if not filename:
            filename = f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'current_metrics': self.get_current_metrics(),
            'average_metrics_5min': self.get_average_metrics(5),
            'average_metrics_15min': self.get_average_metrics(15),
            'all_metrics': self.metrics
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            return filename
        except Exception as e:
            print(f"Error saving metrics report: {e}")
            return None

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
