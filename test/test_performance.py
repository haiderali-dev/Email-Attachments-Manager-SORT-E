#!/usr/bin/env python3
"""
Performance testing suite for email management application
"""

import sys
import os
import time
import unittest
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.performance_monitor import performance_monitor
from services.database_service import db_service
from utils.logger import app_logger

class PerformanceTestSuite(unittest.TestCase):
    """Performance testing suite"""
    
    def setUp(self):
        """Setup for each test"""
        self.start_time = time.time()
        app_logger.log_performance_metric("test_start", self.start_time)
        
    def tearDown(self):
        """Cleanup after each test"""
        end_time = time.time()
        duration = end_time - self.start_time
        app_logger.log_performance_metric("test_duration", duration, "s")
        
    def test_application_startup_time(self):
        """Test application startup performance"""
        start_time = time.time()
        
        # Simulate application startup
        try:
            from main import main
            startup_time = time.time() - start_time
            
            # Startup should be under 2 seconds
            self.assertLess(startup_time, 2.0, f"Startup time {startup_time:.2f}s exceeds 2.0s limit")
            
            app_logger.log_performance_metric("startup_time", startup_time, "s")
            
        except Exception as e:
            self.fail(f"Application startup failed: {e}")
    
    def test_database_connection_performance(self):
        """Test database connection performance"""
        start_time = time.time()
        
        try:
            # Test database connection
            with db_service.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                
            connection_time = time.time() - start_time
            
            # Connection should be under 1 second
            self.assertLess(connection_time, 1.0, f"Database connection time {connection_time:.3f}s exceeds 1.0s limit")
            
            app_logger.log_performance_metric("db_connection_time", connection_time, "s")
            
        except Exception as e:
            self.fail(f"Database connection failed: {e}")
    
    def test_database_query_performance(self):
        """Test database query performance"""
        queries = [
            ("SELECT COUNT(*) FROM emails", "email_count"),
            ("SELECT COUNT(*) FROM tags", "tag_count"),
            ("SELECT COUNT(*) FROM auto_tag_rules", "rule_count"),
            ("SELECT * FROM emails LIMIT 10", "email_sample"),
            ("SELECT * FROM emails WHERE read_status = FALSE LIMIT 10", "unread_emails")
        ]
        
        for query, test_name in queries:
            start_time = time.time()
            
            try:
                result = db_service.execute_query(query)
                query_time = time.time() - start_time
                
                # Queries should be under 0.5 seconds
                self.assertLess(query_time, 0.5, f"Query '{test_name}' took {query_time:.3f}s, exceeds 0.5s limit")
                
                app_logger.log_performance_metric(f"query_time_{test_name}", query_time, "s")
                
            except Exception as e:
                self.fail(f"Query '{test_name}' failed: {e}")
    
    def test_memory_usage(self):
        """Test memory usage during operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform some operations
        for i in range(10):
            db_service.execute_query("SELECT COUNT(*) FROM emails")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (under 50MB)
        self.assertLess(memory_increase, 50.0, f"Memory increase {memory_increase:.1f}MB exceeds 50MB limit")
        
        app_logger.log_performance_metric("memory_increase", memory_increase, "MB")
    
    def test_concurrent_operations(self):
        """Test performance under concurrent operations"""
        import threading
        
        results = []
        errors = []
        
        def perform_operation(operation_id):
            try:
                start_time = time.time()
                db_service.execute_query("SELECT COUNT(*) FROM emails")
                duration = time.time() - start_time
                results.append((operation_id, duration))
            except Exception as e:
                errors.append((operation_id, str(e)))
        
        # Start 5 concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=perform_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check for errors
        self.assertEqual(len(errors), 0, f"Concurrent operations failed: {errors}")
        
        # Calculate average operation time
        if results:
            avg_time = sum(duration for _, duration in results) / len(results)
            self.assertLess(avg_time, 1.0, f"Average concurrent operation time {avg_time:.3f}s exceeds 1.0s limit")
            
            app_logger.log_performance_metric("concurrent_avg_time", avg_time, "s")
    
    def test_large_dataset_performance(self):
        """Test performance with large datasets"""
        # Test with larger result sets
        start_time = time.time()
        
        try:
            # Query with larger limit
            result = db_service.execute_query("SELECT * FROM emails ORDER BY date DESC LIMIT 100")
            query_time = time.time() - start_time
            
            # Large queries should be under 2 seconds
            self.assertLess(query_time, 2.0, f"Large dataset query took {query_time:.3f}s, exceeds 2.0s limit")
            
            app_logger.log_performance_metric("large_dataset_query_time", query_time, "s")
            
        except Exception as e:
            self.fail(f"Large dataset query failed: {e}")
    
    def test_search_performance(self):
        """Test search operation performance"""
        search_queries = [
            "test",
            "email",
            "attachment",
            "important",
            "urgent"
        ]
        
        for query in search_queries:
            start_time = time.time()
            
            try:
                # Simulate search operation
                result = db_service.execute_query(
                    "SELECT * FROM emails WHERE subject LIKE %s OR body LIKE %s LIMIT 50",
                    (f"%{query}%", f"%{query}%")
                )
                
                search_time = time.time() - start_time
                
                # Search should be under 1 second
                self.assertLess(search_time, 1.0, f"Search for '{query}' took {search_time:.3f}s, exceeds 1.0s limit")
                
                app_logger.log_performance_metric(f"search_time_{query}", search_time, "s")
                
            except Exception as e:
                self.fail(f"Search for '{query}' failed: {e}")

class LoadTestSuite(unittest.TestCase):
    """Load testing suite"""
    
    def test_sustained_load(self):
        """Test application performance under sustained load"""
        start_time = time.time()
        operations = 100
        
        for i in range(operations):
            try:
                db_service.execute_query("SELECT COUNT(*) FROM emails")
                
                # Log progress every 10 operations
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    app_logger.log_performance_metric("operations_per_second", rate, "ops/s")
                    
            except Exception as e:
                self.fail(f"Operation {i+1} failed: {e}")
        
        total_time = time.time() - start_time
        avg_time = total_time / operations
        
        # Average operation should be under 0.1 seconds
        self.assertLess(avg_time, 0.1, f"Average operation time {avg_time:.3f}s exceeds 0.1s limit")
        
        app_logger.log_performance_metric("sustained_load_avg_time", avg_time, "s")

def run_performance_tests():
    """Run all performance tests"""
    print("Running Performance Test Suite")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add performance tests
    suite.addTest(unittest.makeSuite(PerformanceTestSuite))
    suite.addTest(unittest.makeSuite(LoadTestSuite))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Performance Test Summary")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All performance tests passed!")
    else:
        print("\n❌ Some performance tests failed!")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_performance_tests()
    sys.exit(0 if success else 1)
