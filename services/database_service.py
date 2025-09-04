import mysql.connector
import datetime
import time
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from config.database import DB_CONFIG

class DatabaseService:
    """Database connection and operations service"""
    
    def __init__(self):
        self.config = DB_CONFIG.copy()
        self.query_stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'query_times': [],
            'errors': 0
        }
        self.slow_query_threshold = 1.0  # seconds

    @contextmanager
    def get_connection(self):
        """
        Get database connection with context manager
        
        Usage:
            with db_service.get_connection() as conn:
                cursor = conn.cursor()
                # ... database operations
        """
        conn = None
        try:
            conn = mysql.connector.connect(**self.config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.query_stats['errors'] += 1
            raise e
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Any:
        """
        Execute a database query with performance monitoring
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results
        """
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                    conn.commit()
                
                cursor.close()
                
                # Record query performance
                query_time = time.time() - start_time
                self.query_stats['total_queries'] += 1
                self.query_stats['query_times'].append(query_time)
                
                if query_time > self.slow_query_threshold:
                    self.query_stats['slow_queries'] += 1
                    print(f"SLOW QUERY ({query_time:.2f}s): {query[:100]}...")
                
                # Keep only last 1000 query times
                if len(self.query_stats['query_times']) > 1000:
                    self.query_stats['query_times'] = self.query_stats['query_times'][-1000:]
                
                return result
                
        except Exception as e:
            self.query_stats['errors'] += 1
            raise e

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get database performance statistics"""
        if not self.query_stats['query_times']:
            return {
                'total_queries': 0,
                'slow_queries': 0,
                'avg_query_time': 0,
                'max_query_time': 0,
                'error_rate': 0
            }
        
        avg_time = sum(self.query_stats['query_times']) / len(self.query_stats['query_times'])
        max_time = max(self.query_stats['query_times'])
        error_rate = (self.query_stats['errors'] / self.query_stats['total_queries']) * 100 if self.query_stats['total_queries'] > 0 else 0
        
        return {
            'total_queries': self.query_stats['total_queries'],
            'slow_queries': self.query_stats['slow_queries'],
            'avg_query_time': round(avg_time, 3),
            'max_query_time': round(max_time, 3),
            'error_rate': round(error_rate, 2),
            'slow_query_percentage': round((self.query_stats['slow_queries'] / self.query_stats['total_queries']) * 100, 2) if self.query_stats['total_queries'] > 0 else 0
        }

    def optimize_database(self) -> Dict[str, Any]:
        """Perform database optimization tasks"""
        results = {}
        
        try:
            # Analyze tables
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get list of tables
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        cursor.execute(f"ANALYZE TABLE {table}")
                        results[f"analyze_{table}"] = "success"
                    except Exception as e:
                        results[f"analyze_{table}"] = f"error: {str(e)}"
                
                cursor.close()
                
        except Exception as e:
            results['error'] = str(e)
        
        return results

    def create_unified_database(self):
        """Create unified database with all necessary tables"""
        tmp = mysql.connector.connect(
            host=self.config['host'],
            user=self.config['user'],
            password=self.config['password']
        )
        cur = tmp.cursor()
        # Validate database name to prevent SQL injection
        db_name = self.config['database']
        if not db_name.replace('_', '').replace('-', '').isalnum():
            raise ValueError(f"Invalid database name: {db_name}")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cur.close()
        tmp.close()

        conn = mysql.connector.connect(**self.config)
        cursor = conn.cursor()

        # Dashboard users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                failed_attempts INT DEFAULT 0,
                locked_until TIMESTAMP NULL,
                reset_token VARCHAR(10) NULL,
                reset_token_expiry TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL
            )
        """)

        # Email accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                dashboard_user_id INT NOT NULL,
                imap_host VARCHAR(255),
                email VARCHAR(255),
                encrypted_password BLOB,
                last_sync TIMESTAMP NULL,
                sync_enabled BOOLEAN DEFAULT TRUE,
                session_expires TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_email (dashboard_user_id, email)
            )
        """)

        # Emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INT AUTO_INCREMENT PRIMARY KEY,
                uid VARCHAR(255),
                subject TEXT,
                sender TEXT,
                recipients TEXT,
                date DATETIME,
                has_attachment BOOLEAN DEFAULT FALSE,
                body LONGTEXT,
                body_text LONGTEXT,
                body_html LONGTEXT,
                body_format ENUM('text', 'html', 'both') DEFAULT 'text',
                size_bytes INT DEFAULT 0,
                read_status BOOLEAN DEFAULT FALSE,
                priority ENUM('high','normal','low') DEFAULT 'normal',
                account_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                UNIQUE KEY(uid, account_id),
                INDEX idx_date (date),
                INDEX idx_sender (sender(100)),
                INDEX idx_subject (subject(100)),
                INDEX idx_body_format (body_format)
            )
        """)

        # Tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                color VARCHAR(7) DEFAULT '#2196F3',
                dashboard_user_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_tag (dashboard_user_id, name)
            )
        """)

        # Email tags junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_tags (
                email_id INT,
                tag_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(email_id, tag_id),
                FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)

        # Auto tag rules with attachment saving
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_tag_rules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                rule_type ENUM('sender','subject','body','domain') NOT NULL,
                operator ENUM('contains','equals','starts_with','ends_with','regex') DEFAULT 'contains',
                value TEXT NOT NULL,
                tag_id INT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                priority INT DEFAULT 0,
                save_attachments BOOLEAN DEFAULT FALSE,
                attachment_path TEXT NULL,
                dashboard_user_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
            )
        """)

        # Search history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                query TEXT NOT NULL,
                search_type VARCHAR(50),
                dashboard_user_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
            )
        """)

        # Attachments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email_id INT NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_path TEXT NOT NULL,
                file_size INT DEFAULT 0,
                mime_type VARCHAR(100),
                content_type VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
                INDEX idx_email_id (email_id),
                INDEX idx_filename (filename(100)),
                INDEX idx_mime_type (mime_type)
            )
        """)

        # Device attachments table (for tracking files saved to device)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_attachments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                attachment_id INT NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                device_filename VARCHAR(255) NOT NULL,
                device_path TEXT NOT NULL,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (attachment_id) REFERENCES attachments(id) ON DELETE CASCADE,
                INDEX idx_attachment_id (attachment_id),
                INDEX idx_original_filename (original_filename(100)),
                INDEX idx_device_filename (device_filename(100))
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()

    def get_database_size(self) -> Dict[str, Any]:
        """Get database size information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get database size
                cursor.execute("""
                    SELECT 
                        table_schema AS 'Database',
                        ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                    GROUP BY table_schema
                """, (self.config['database'],))
                
                db_size = cursor.fetchone()
                
                # Get table sizes
                cursor.execute("""
                    SELECT 
                        table_name AS 'Table',
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)',
                        table_rows AS 'Rows'
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                    ORDER BY (data_length + index_length) DESC
                """, (self.config['database'],))
                
                table_sizes = cursor.fetchall()
                
                cursor.close()
                
                return {
                    'database_size_mb': db_size[1] if db_size else 0,
                    'tables': table_sizes
                }
                
        except Exception as e:
            return {'error': str(e)}

    def clean_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """
        Clean old data from database
        
        Args:
            days_to_keep: Number of days of data to keep
            
        Returns:
            Dictionary with cleanup results
        """
        results = {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clean old search history
                cursor.execute("""
                    DELETE FROM search_history 
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days_to_keep,))
                results['search_history'] = cursor.rowcount
                
                # Clean expired sessions
                cursor.execute("""
                    UPDATE accounts 
                    SET sync_enabled = FALSE 
                    WHERE session_expires IS NOT NULL 
                    AND session_expires < NOW()
                """)
                results['expired_sessions'] = cursor.rowcount
                
                conn.commit()
                cursor.close()
                
        except Exception as e:
            results['error'] = str(e)
        
        return results

# Global database service instance
db_service = DatabaseService() 