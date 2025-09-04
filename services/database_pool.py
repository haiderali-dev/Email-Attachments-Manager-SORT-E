import mysql.connector
import threading
import time
import queue
from typing import Optional, Dict, Any
from contextlib import contextmanager
from config.database import DB_CONFIG

# Try to import performance optimizer, fallback to None if not available
try:
    from utils.performance_optimizer import performance_optimizer
except ImportError:
    performance_optimizer = None
    print("Warning: Performance optimizer not available, database pool will run without performance tracking")

class DatabaseConnectionPool:
    """High-performance database connection pool for the email manager"""
    
    def __init__(self, max_connections: int = 10, connection_timeout: int = 30):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.pool = queue.Queue(maxsize=max_connections)
        self.active_connections = 0
        self.total_connections_created = 0
        self.connection_stats = {
            'created': 0,
            'reused': 0,
            'failed': 0,
            'timeout': 0
        }
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Initialize pool with some connections
        self._initialize_pool()
        
        # Start connection health check
        self._start_health_check()
    
    def _initialize_pool(self):
        """Initialize the connection pool with initial connections"""
        try:
            for _ in range(min(3, self.max_connections)):
                conn = self._create_connection()
                if conn:
                    self.pool.put(conn)
                    self.total_connections_created += 1
        except Exception as e:
            print(f"Failed to initialize connection pool: {e}")
    
    def _create_connection(self) -> Optional[mysql.connector.MySQLConnection]:
        """Create a new database connection"""
        try:
            # Create connection with proper configuration
            conn = mysql.connector.connect(**DB_CONFIG)
            
            # Configure connection for performance
            conn.autocommit = False  # Use transactions for better performance
            
            # Set session variables for performance using SQL commands
            cursor = conn.cursor()
            cursor.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
            cursor.execute("SET SESSION innodb_lock_wait_timeout = 50")
            cursor.execute("SET SESSION wait_timeout = 28800")  # 8 hours
            cursor.execute("SET SESSION character_set_connection = 'utf8mb4'")
            cursor.execute("SET SESSION collation_connection = 'utf8mb4_unicode_ci'")
            cursor.close()
            
            return conn
            
        except Exception as e:
            print(f"Failed to create database connection: {e}")
            self.connection_stats['failed'] += 1
            return None
    
    def _start_health_check(self):
        """Start background connection health check"""
        def health_check():
            while True:
                try:
                    self._check_connection_health()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    print(f"Health check error: {e}")
                    time.sleep(60)
        
        health_thread = threading.Thread(target=health_check, daemon=True)
        health_thread.start()
    
    def _check_connection_health(self):
        """Check health of connections in the pool"""
        with self.lock:
            # Check if connections are still valid
            valid_connections = []
            
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    if self._is_connection_valid(conn):
                        valid_connections.append(conn)
                    else:
                        conn.close()
                        self.active_connections -= 1
                except queue.Empty:
                    break
            
            # Put valid connections back in the pool
            for conn in valid_connections:
                self.pool.put(conn)
            
            # Replenish pool if needed
            while self.pool.qsize() < min(3, self.max_connections):
                conn = self._create_connection()
                if conn:
                    self.pool.put(conn)
                    self.total_connections_created += 1
    
    def _is_connection_valid(self, conn: mysql.connector.MySQLConnection) -> bool:
        """Check if a connection is still valid"""
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except:
            return False
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool"""
        conn = None
        start_time = time.time()
        
        try:
            # Try to get connection from pool
            try:
                conn = self.pool.get(timeout=5)  # 5 second timeout
                self.connection_stats['reused'] += 1
            except queue.Empty:
                # Pool is empty, create new connection if possible
                with self.lock:
                    if self.active_connections < self.max_connections:
                        conn = self._create_connection()
                        if conn:
                            self.active_connections += 1
                            self.total_connections_created += 1
                            self.connection_stats['created'] += 1
                        else:
                            raise Exception("Failed to create database connection")
                    else:
                        raise Exception("Maximum database connections reached")
            
            # Track connection usage if performance optimizer is available
            if performance_optimizer:
                try:
                    performance_optimizer.cache_result(
                        f"db_connection_{id(conn)}",
                        {
                            'acquired_at': time.time(),
                            'pool_size': self.pool.qsize(),
                            'active_connections': self.active_connections
                        },
                        ttl=300
                    )
                except Exception as e:
                    print(f"Performance tracking error: {e}")
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.close()
                with self.lock:
                    self.active_connections -= 1
            raise e
        
        finally:
            if conn:
                # Return connection to pool if it's still valid
                if self._is_connection_valid(conn):
                    try:
                        # Reset connection state
                        conn.rollback()
                        self.pool.put(conn)
                    except queue.Full:
                        # Pool is full, close the connection
                        conn.close()
                        with self.lock:
                            self.active_connections -= 1
                else:
                    # Connection is invalid, close it
                    conn.close()
                    with self.lock:
                        self.active_connections -= 1
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Any:
        """Execute a database query using connection pool"""
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # Optimize query if possible (basic optimization)
                optimized_query = self._optimize_query(query)
                
                if params:
                    cursor.execute(optimized_query, params)
                else:
                    cursor.execute(optimized_query)
                
                if fetch:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                    conn.commit()
                
                cursor.close()
                
                # Cache query result for performance if available
                if performance_optimizer and fetch and result:
                    try:
                        query_hash = hash(f"{query}{str(params)}")
                        performance_optimizer.cache_result(
                            f"query_result_{query_hash}",
                            result,
                            ttl=60  # Cache for 1 minute
                        )
                    except Exception as e:
                        print(f"Query caching error: {e}")
                
                return result
                
        except Exception as e:
            # Log error if performance optimizer is available
            if performance_optimizer:
                try:
                    performance_optimizer.cache_result(
                        f"query_error_{int(time.time())}",
                        {
                            'query': query[:100],
                            'error': str(e),
                            'timestamp': time.time()
                        },
                        ttl=3600
                    )
                except Exception as cache_error:
                    print(f"Error logging error: {cache_error}")
            raise e
    
    def _optimize_query(self, query: str) -> str:
        """Basic query optimization"""
        optimized_query = query.strip()
        
        # Add LIMIT if not present for large result sets
        if 'LIMIT' not in optimized_query.upper() and 'SELECT' in optimized_query.upper():
            if 'WHERE' in optimized_query.upper():
                optimized_query += ' LIMIT 1000'
            else:
                optimized_query += ' LIMIT 500'
        
        return optimized_query
    
    def execute_transaction(self, queries: list) -> bool:
        """Execute multiple queries in a transaction"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for query, params in queries:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                
                conn.commit()
                cursor.close()
                return True
                
        except Exception as e:
            print(f"Transaction error: {e}")
            return False
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self.lock:
            return {
                'pool_size': self.pool.qsize(),
                'active_connections': self.active_connections,
                'max_connections': self.max_connections,
                'total_created': self.total_connections_created,
                'connection_stats': self.connection_stats.copy(),
                'pool_utilization': (self.active_connections / self.max_connections) * 100
            }
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        with self.lock:
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    conn.close()
                except queue.Empty:
                    break
            
            self.active_connections = 0

# Global database pool instance
db_pool = DatabaseConnectionPool()
