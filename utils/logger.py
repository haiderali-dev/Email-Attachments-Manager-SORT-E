import logging
import os
import sys
from datetime import datetime
from typing import Optional
import traceback

class ApplicationLogger:
    """Comprehensive logging system for the email management application"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Create loggers
        self.setup_loggers()
        
    def setup_loggers(self):
        """Setup different loggers for different purposes"""
        
        # Main application logger
        self.app_logger = logging.getLogger('email_manager')
        self.app_logger.setLevel(logging.INFO)
        
        # Performance logger
        self.perf_logger = logging.getLogger('email_manager.performance')
        self.perf_logger.setLevel(logging.INFO)
        
        # Database logger
        self.db_logger = logging.getLogger('email_manager.database')
        self.db_logger.setLevel(logging.INFO)
        
        # Email operations logger
        self.email_logger = logging.getLogger('email_manager.email')
        self.email_logger.setLevel(logging.INFO)
        
        # Security logger
        self.security_logger = logging.getLogger('email_manager.security')
        self.security_logger.setLevel(logging.INFO)
        
        # Setup handlers for each logger
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup file and console handlers for all loggers"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Main application log
        app_handler = logging.FileHandler(os.path.join(self.log_dir, f'app_{today}.log'))
        app_handler.setFormatter(self._get_formatter())
        self.app_logger.addHandler(app_handler)
        
        # Performance log
        perf_handler = logging.FileHandler(os.path.join(self.log_dir, f'performance_{today}.log'))
        perf_handler.setFormatter(self._get_formatter())
        self.perf_logger.addHandler(perf_handler)
        
        # Database log
        db_handler = logging.FileHandler(os.path.join(self.log_dir, f'database_{today}.log'))
        db_handler.setFormatter(self._get_formatter())
        self.db_logger.addHandler(db_handler)
        
        # Email operations log
        email_handler = logging.FileHandler(os.path.join(self.log_dir, f'email_{today}.log'))
        email_handler.setFormatter(self._get_formatter())
        self.email_logger.addHandler(email_handler)
        
        # Security log
        security_handler = logging.FileHandler(os.path.join(self.log_dir, f'security_{today}.log'))
        security_handler.setFormatter(self._get_formatter())
        self.security_logger.addHandler(security_handler)
        
        # Console handler for main logger
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._get_console_formatter())
        self.app_logger.addHandler(console_handler)
        
    def _get_formatter(self):
        """Get detailed formatter for file logs"""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
    
    def _get_console_formatter(self):
        """Get simple formatter for console output"""
        return logging.Formatter('%(levelname)s: %(message)s')
    
    def log_application_start(self):
        """Log application startup"""
        self.app_logger.info("Application started")
        
    def log_application_stop(self):
        """Log application shutdown"""
        self.app_logger.info("Application stopped")
        
    def log_user_login(self, user_id: int, username: str, success: bool):
        """Log user login attempts"""
        if success:
            self.security_logger.info(f"Successful login - User ID: {user_id}, Username: {username}")
        else:
            self.security_logger.warning(f"Failed login attempt - Username: {username}")
            
    def log_email_sync(self, account_id: int, email_count: int, duration: float, success: bool):
        """Log email synchronization operations"""
        if success:
            self.email_logger.info(f"Email sync completed - Account: {account_id}, Emails: {email_count}, Duration: {duration:.2f}s")
        else:
            self.email_logger.error(f"Email sync failed - Account: {account_id}, Duration: {duration:.2f}s")
            
    def log_database_operation(self, operation: str, table: str, duration: float, success: bool, error: str = None):
        """Log database operations"""
        if success:
            self.db_logger.info(f"DB {operation} - Table: {table}, Duration: {duration:.3f}s")
        else:
            self.db_logger.error(f"DB {operation} failed - Table: {table}, Duration: {duration:.3f}s, Error: {error}")
            
    def log_performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """Log performance metrics"""
        self.perf_logger.info(f"Performance - {metric_name}: {value}{unit}")
        
    def log_error(self, error: Exception, context: str = "", user_id: Optional[int] = None):
        """Log application errors with full context"""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'user_id': user_id,
            'traceback': traceback.format_exc()
        }
        
        self.app_logger.error(f"Application error: {error_info}")
        
    def log_security_event(self, event_type: str, details: str, user_id: Optional[int] = None):
        """Log security-related events"""
        self.security_logger.info(f"Security event - Type: {event_type}, Details: {details}, User ID: {user_id}")
        
    def log_attachment_operation(self, operation: str, filename: str, size: int, success: bool):
        """Log attachment operations"""
        if success:
            self.email_logger.info(f"Attachment {operation} - File: {filename}, Size: {size} bytes")
        else:
            self.email_logger.error(f"Attachment {operation} failed - File: {filename}")
            
    def log_search_operation(self, query: str, result_count: int, duration: float, user_id: int):
        """Log search operations"""
        self.app_logger.info(f"Search - Query: '{query}', Results: {result_count}, Duration: {duration:.3f}s, User: {user_id}")
        
    def log_rule_application(self, rule_id: int, email_id: int, success: bool):
        """Log auto-tag rule applications"""
        if success:
            self.app_logger.info(f"Rule applied - Rule ID: {rule_id}, Email ID: {email_id}")
        else:
            self.app_logger.warning(f"Rule application failed - Rule ID: {rule_id}, Email ID: {email_id}")
            
    def get_recent_logs(self, log_type: str = "app", lines: int = 50) -> list:
        """Get recent log entries"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(self.log_dir, f'{log_type}_{today}.log')
            
            if not os.path.exists(log_file):
                return []
                
            with open(log_file, 'r', encoding='utf-8') as f:
                lines_list = f.readlines()
                return lines_list[-lines:] if len(lines_list) > lines else lines_list
                
        except Exception as e:
            return [f"Error reading logs: {e}"]
            
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old log files"""
        try:
            import glob
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for log_file in glob.glob(os.path.join(self.log_dir, "*.log")):
                file_date_str = os.path.basename(log_file).split('_')[1].split('.')[0]
                try:
                    file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                    if file_date < cutoff_date:
                        os.remove(log_file)
                        self.app_logger.info(f"Cleaned up old log file: {log_file}")
                except ValueError:
                    # Skip files that don't match the expected format
                    continue
                    
        except Exception as e:
            self.app_logger.error(f"Error cleaning up old logs: {e}")

# Global logger instance
app_logger = ApplicationLogger()
