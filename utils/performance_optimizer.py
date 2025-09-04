"""
Performance optimization utilities for the email management application
"""

import time
import threading
import weakref
from typing import Dict, Any, Optional, Callable, List
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QObject, QEvent
from PyQt5.QtWidgets import QApplication
import gc
import psutil
import os

class PerformanceOptimizer(QObject):
    """Comprehensive performance optimization system for the email manager"""
    
    # Performance signals
    performance_warning = pyqtSignal(str, str)  # level, message
    optimization_completed = pyqtSignal(str)    # optimization_type
    
    def __init__(self):
        super().__init__()
        self.optimization_active = False
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = 300  # 5 minutes default TTL
        self.memory_threshold = 80  # 80% memory usage threshold
        self.gc_threshold = 1000  # Garbage collection threshold
        
        # Performance monitoring
        self.last_gc_time = time.time()
        self.query_cache = {}
        self.ui_update_times = []
        
        # Start background optimization
        self.start_background_optimization()
    
    def start_background_optimization(self):
        """Start background performance optimization thread"""
        self.optimization_active = True
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
    
    def stop_background_optimization(self):
        """Stop background optimization"""
        self.optimization_active = False
        if hasattr(self, 'optimization_thread'):
            self.optimization_thread.join(timeout=1)
    
    def _optimization_loop(self):
        """Background optimization loop"""
        while self.optimization_active:
            try:
                # Memory optimization
                self._optimize_memory()
                
                # Cache cleanup
                self._cleanup_cache()
                
                # Garbage collection
                self._smart_garbage_collection()
                
                # UI responsiveness check
                self._check_ui_responsiveness()
                
                time.sleep(10)  # Run every 10 seconds
                
            except Exception as e:
                print(f"Performance optimization error: {e}")
    
    def _optimize_memory(self):
        """Optimize memory usage"""
        try:
            memory = psutil.virtual_memory()
            if memory.percent > self.memory_threshold:
                # Force garbage collection
                collected = gc.collect()
                if collected > 0:
                    self.performance_warning.emit("warning", f"Memory usage high ({memory.percent}%), cleaned {collected} objects")
                
                # Clear old cache entries
                self._clear_old_cache_entries()
                
        except Exception as e:
            print(f"Memory optimization error: {e}")
    
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, timestamp in self.cache_timestamps.items():
            if current_time - timestamp > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            del self.cache_timestamps[key]
    
    def _smart_garbage_collection(self):
        """Smart garbage collection based on thresholds"""
        current_time = time.time()
        
        # Only run GC if enough time has passed and we have many objects
        if (current_time - self.last_gc_time > 60 and  # At least 1 minute apart
            len(gc.get_objects()) > self.gc_threshold):
            
            collected = gc.collect()
            self.last_gc_time = current_time
            
            if collected > 0:
                print(f"Garbage collection: cleaned {collected} objects")
    
    def _check_ui_responsiveness(self):
        """Check UI responsiveness and optimize if needed"""
        if len(self.ui_update_times) > 10:
            # Calculate average UI update time
            avg_time = sum(self.ui_update_times) / len(self.ui_update_times)
            
            if avg_time > 0.1:  # More than 100ms average
                self.performance_warning.emit("warning", f"UI responsiveness degraded (avg: {avg_time:.3f}s)")
                
                # Force a UI update to improve responsiveness
                QApplication.processEvents()
            
            # Keep only recent times
            self.ui_update_times = self.ui_update_times[-10:]
    
    def cache_result(self, key: str, data: Any, ttl: int = None):
        """Cache a result with TTL"""
        self.cache[key] = data
        self.cache_timestamps[key] = time.time()
        
        if ttl:
            # Schedule cleanup
            QTimer.singleShot(ttl * 1000, lambda: self._remove_cache_entry(key))
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result if not expired"""
        if key in self.cache:
            timestamp = self.cache_timestamps.get(key, 0)
            if time.time() - timestamp < self.cache_ttl:
                return self.cache[key]
            else:
                # Remove expired entry
                del self.cache[key]
                del self.cache_timestamps[key]
        return None
    
    def _remove_cache_entry(self, key: str):
        """Remove a cache entry"""
        if key in self.cache:
            del self.cache[key]
            del self.cache_timestamps[key]
    
    def _clear_old_cache_entries(self):
        """Clear old cache entries to free memory"""
        current_time = time.time()
        keys_to_remove = []
        
        for key, timestamp in self.cache_timestamps.items():
            if current_time - timestamp > self.cache_ttl * 2:  # Remove entries older than 2x TTL
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
            del self.cache_timestamps[key]
    
    def optimize_database_queries(self, query: str, params: tuple = None) -> str:
        """Optimize database queries for better performance"""
        # Simple query optimization
        optimized_query = query.strip()
        
        # Add LIMIT if not present for large result sets
        if 'LIMIT' not in optimized_query.upper() and 'SELECT' in optimized_query.upper():
            if 'WHERE' in optimized_query.upper():
                optimized_query += ' LIMIT 1000'
            else:
                optimized_query += ' LIMIT 500'
        
        return optimized_query
    
    def measure_ui_update_time(self, func: Callable) -> Callable:
        """Decorator to measure UI update time"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            update_time = time.time() - start_time
            
            self.ui_update_times.append(update_time)
            
            # Keep only recent measurements
            if len(self.ui_update_times) > 20:
                self.ui_update_times = self.ui_update_times[-20:]
            
            return result
        return wrapper
    
    def optimize_list_widget(self, list_widget, max_items: int = 1000):
        """Optimize list widget performance"""
        if hasattr(list_widget, 'count') and list_widget.count() > max_items:
            # Remove old items to maintain performance
            items_to_remove = list_widget.count() - max_items
            for _ in range(items_to_remove):
                list_widget.takeItem(0)
    
    def optimize_table_widget(self, table_widget, max_rows: int = 500):
        """Optimize table widget performance"""
        if hasattr(table_widget, 'rowCount') and table_widget.rowCount() > max_rows:
            # Remove old rows to maintain performance
            rows_to_remove = table_widget.rowCount() - max_rows
            table_widget.setRowCount(max_rows)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        try:
            memory = psutil.virtual_memory()
            return {
                'memory_usage_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'cache_size': len(self.cache),
                'cache_hit_rate': self._calculate_cache_hit_rate(),
                'ui_responsiveness': self._calculate_ui_responsiveness(),
                'garbage_collection_count': gc.get_count(),
                'active_threads': threading.active_count()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if not hasattr(self, '_cache_hits'):
            self._cache_hits = 0
            self._cache_misses = 0
        
        total = self._cache_hits + self._cache_misses
        return (self._cache_hits / total * 100) if total > 0 else 0
    
    def _calculate_ui_responsiveness(self) -> float:
        """Calculate UI responsiveness score"""
        if not self.ui_update_times:
            return 100.0
        
        avg_time = sum(self.ui_update_times) / len(self.ui_update_times)
        # Convert to responsiveness score (0-100, higher is better)
        if avg_time <= 0.016:  # 60 FPS
            return 100.0
        elif avg_time <= 0.033:  # 30 FPS
            return 80.0
        elif avg_time <= 0.1:  # 10 FPS
            return 60.0
        else:
            return max(0, 100 - (avg_time * 1000))
    
    def force_optimization(self):
        """Force immediate optimization"""
        self._optimize_memory()
        self._cleanup_cache()
        collected = gc.collect()
        self.optimization_completed.emit(f"Immediate optimization completed, cleaned {collected} objects")

# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


