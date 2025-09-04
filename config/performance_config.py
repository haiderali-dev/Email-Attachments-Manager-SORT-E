import json
import os
from typing import Dict, Any
import time

class PerformanceConfig:
    """Performance configuration management for the email manager"""
    
    DEFAULT_CONFIG = {
        # Memory management
        'memory_threshold': 80,  # Percentage
        'gc_threshold': 1000,    # Objects
        'gc_interval': 60,       # Seconds
        
        # Cache settings
        'cache_ttl': 300,        # 5 minutes
        'max_cache_size': 1000,  # Items
        'cache_cleanup_interval': 300,  # 5 minutes
        
        # UI optimization
        'max_items_per_widget': 1000,
        'max_rows_per_table': 500,
        'max_tree_items': 300,
        'update_batch_size': 50,
        'update_delay_ms': 16,   # ~60 FPS
        
        # Database optimization
        'max_connections': 10,
        'connection_timeout': 30,
        'query_cache_ttl': 60,   # 1 minute
        'slow_query_threshold': 1.0,  # Seconds
        
        # Email processing
        'progressive_batch_size': 100,
        'progressive_commit_interval': 100,
        'max_concurrent_fetches': 3,
        
        # Background optimization
        'optimization_interval': 10,  # Seconds
        'health_check_interval': 60,  # Seconds
        
        # Performance monitoring
        'monitoring_enabled': True,
        'metrics_retention': 1000,  # Entries
        'performance_warnings': True,
        
        # Startup optimization
        'deferred_initialization': True,
        'lazy_loading': True,
        'startup_delay': 100,  # Milliseconds
    }
    
    def __init__(self, config_file: str = 'performance_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load performance configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded_config)
                    return config
            else:
                # Create default config file
                self.save_config(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG
        except Exception as e:
            print(f"Error loading performance config: {e}")
            return self.DEFAULT_CONFIG
    
    def save_config(self, config: Dict[str, Any] = None):
        """Save performance configuration to file"""
        try:
            if config is None:
                config = self.config
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            # Update current config
            self.config = config
            
        except Exception as e:
            print(f"Error saving performance config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple configuration values"""
        self.config.update(updates)
        self.save_config()
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()
    
    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory management configuration"""
        return {
            'threshold': self.get('memory_threshold'),
            'gc_threshold': self.get('gc_threshold'),
            'gc_interval': self.get('gc_interval')
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration"""
        return {
            'ttl': self.get('cache_ttl'),
            'max_size': self.get('max_cache_size'),
            'cleanup_interval': self.get('cache_cleanup_interval')
        }
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI optimization configuration"""
        return {
            'max_items_per_widget': self.get('max_items_per_widget'),
            'max_rows_per_table': self.get('max_rows_per_table'),
            'max_tree_items': self.get('max_tree_items'),
            'update_batch_size': self.get('update_batch_size'),
            'update_delay_ms': self.get('update_delay_ms')
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database optimization configuration"""
        return {
            'max_connections': self.get('max_connections'),
            'connection_timeout': self.get('connection_timeout'),
            'query_cache_ttl': self.get('query_cache_ttl'),
            'slow_query_threshold': self.get('slow_query_threshold')
        }
    
    def get_email_config(self) -> Dict[str, Any]:
        """Get email processing configuration"""
        return {
            'progressive_batch_size': self.get('progressive_batch_size'),
            'progressive_commit_interval': self.get('progressive_commit_interval'),
            'max_concurrent_fetches': self.get('max_concurrent_fetches')
        }
    
    def get_optimization_config(self) -> Dict[str, Any]:
        """Get background optimization configuration"""
        return {
            'interval': self.get('optimization_interval'),
            'health_check_interval': self.get('health_check_interval'),
            'monitoring_enabled': self.get('monitoring_enabled')
        }
    
    def get_startup_config(self) -> Dict[str, Any]:
        """Get startup optimization configuration"""
        return {
            'deferred_initialization': self.get('deferred_initialization'),
            'lazy_loading': self.get('lazy_loading'),
            'startup_delay': self.get('startup_delay')
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration values and return any issues"""
        issues = {}
        
        # Memory validation
        if not 50 <= self.get('memory_threshold') <= 95:
            issues['memory_threshold'] = 'Must be between 50 and 95'
        
        if not 100 <= self.get('gc_threshold') <= 10000:
            issues['gc_threshold'] = 'Must be between 100 and 10000'
        
        # Cache validation
        if not 60 <= self.get('cache_ttl') <= 3600:
            issues['cache_ttl'] = 'Must be between 60 and 3600 seconds'
        
        if not 100 <= self.get('max_cache_size') <= 10000:
            issues['max_cache_size'] = 'Must be between 100 and 10000'
        
        # UI validation
        if not 100 <= self.get('max_items_per_widget') <= 10000:
            issues['max_items_per_widget'] = 'Must be between 100 and 10000'
        
        if not 10 <= self.get('update_delay_ms') <= 100:
            issues['update_delay_ms'] = 'Must be between 10 and 100 milliseconds'
        
        # Database validation
        if not 1 <= self.get('max_connections') <= 50:
            issues['max_connections'] = 'Must be between 1 and 50'
        
        if not 0.1 <= self.get('slow_query_threshold') <= 10.0:
            issues['slow_query_threshold'] = 'Must be between 0.1 and 10.0 seconds'
        
        return issues
    
    def get_recommended_config(self, system_type: str = 'desktop') -> Dict[str, Any]:
        """Get recommended configuration for different system types"""
        if system_type == 'low_end':
            return {
                'memory_threshold': 70,
                'gc_threshold': 500,
                'max_items_per_widget': 500,
                'max_rows_per_table': 250,
                'max_cache_size': 500,
                'max_connections': 5,
                'progressive_batch_size': 50
            }
        elif system_type == 'high_end':
            return {
                'memory_threshold': 90,
                'gc_threshold': 2000,
                'max_items_per_widget': 2000,
                'max_rows_per_table': 1000,
                'max_cache_size': 2000,
                'max_connections': 20,
                'progressive_batch_size': 200
            }
        else:  # desktop (default)
            return self.DEFAULT_CONFIG
    
    def apply_system_optimization(self, system_type: str = 'desktop'):
        """Apply system-specific optimization settings"""
        recommended = self.get_recommended_config(system_type)
        self.update(recommended)
        return recommended
    
    def export_config(self, filename: str = None) -> str:
        """Export configuration to file"""
        if not filename:
            filename = f"performance_config_export_{int(time.time())}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.config, f, indent=4)
            return filename
        except Exception as e:
            print(f"Error exporting config: {e}")
            return None
    
    def import_config(self, filename: str) -> bool:
        """Import configuration from file"""
        try:
            with open(filename, 'r') as f:
                imported_config = json.load(f)
            
            # Validate imported config
            issues = self.validate_config()
            if issues:
                print(f"Import validation issues: {issues}")
                return False
            
            self.update(imported_config)
            return True
            
        except Exception as e:
            print(f"Error importing config: {e}")
            return False

# Global performance configuration instance
performance_config = PerformanceConfig()

# Utility functions for easy access
def get_perf_config(key: str, default: Any = None) -> Any:
    """Get performance configuration value"""
    return performance_config.get(key, default)

def set_perf_config(key: str, value: Any):
    """Set performance configuration value"""
    performance_config.set(key, value)

def update_perf_config(updates: Dict[str, Any]):
    """Update multiple performance configuration values"""
    performance_config.update(updates)
