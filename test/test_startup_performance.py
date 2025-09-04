#!/usr/bin/env python3
"""
Test script to verify startup performance improvements
"""

import sys
import os
import time
import unittest
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.performance_optimizer import PerformanceOptimizer, StartupOptimizer

class StartupPerformanceTest(unittest.TestCase):
    """Test startup performance optimizations"""
    
    def setUp(self):
        """Setup for each test"""
        self.start_time = time.time()
        
    def tearDown(self):
        """Cleanup after each test"""
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test completed in {duration:.3f} seconds")
        
    def test_performance_optimizer_defer(self):
        """Test deferred operation functionality"""
        start_time = time.time()
        
        # Test deferred operation
        operation_completed = False
        def test_operation():
            nonlocal operation_completed
            operation_completed = True
        
        PerformanceOptimizer.defer_operation(100, test_operation)
        
        # Wait a bit for the operation to complete
        time.sleep(0.2)
        
        self.assertTrue(operation_completed, "Deferred operation should complete")
        
        execution_time = time.time() - start_time
        self.assertLess(execution_time, 0.5, f"Deferred operation took too long: {execution_time:.3f}s")
        
    def test_startup_optimizer(self):
        """Test startup task optimization"""
        start_time = time.time()
        
        startup_optimizer = StartupOptimizer()
        tasks_completed = []
        
        def task1():
            time.sleep(0.1)  # Simulate work
            tasks_completed.append("task1")
            
        def task2():
            time.sleep(0.1)  # Simulate work
            tasks_completed.append("task2")
            
        def task3():
            time.sleep(0.1)  # Simulate work
            tasks_completed.append("task3")
        
        # Add tasks with different priorities
        startup_optimizer.add_startup_task("task1", task1, priority=1)
        startup_optimizer.add_startup_task("task2", task2, priority=2)
        startup_optimizer.add_startup_task("task3", task3, priority=3)
        
        # Execute tasks
        startup_optimizer.execute_startup_tasks(delay_ms=50)
        
        # Wait for all tasks to complete
        time.sleep(0.5)
        
        # Check if all tasks completed
        self.assertEqual(len(tasks_completed), 3, "All tasks should complete")
        self.assertTrue("task1" in tasks_completed, "Task1 should complete")
        self.assertTrue("task2" in tasks_completed, "Task2 should complete")
        self.assertTrue("task3" in tasks_completed, "Task3 should complete")
        
        execution_time = time.time() - start_time
        self.assertLess(execution_time, 1.0, f"Startup optimization took too long: {execution_time:.3f}s")
        
    def test_batch_operations(self):
        """Test batch operation functionality"""
        start_time = time.time()
        
        operations_completed = []
        
        def op1():
            operations_completed.append("op1")
            
        def op2():
            operations_completed.append("op2")
            
        def op3():
            operations_completed.append("op3")
            
        def op4():
            operations_completed.append("op4")
            
        def op5():
            operations_completed.append("op5")
        
        operations = [
            (op1, (), {}),
            (op2, (), {}),
            (op3, (), {}),
            (op4, (), {}),
            (op5, (), {})
        ]
        
        PerformanceOptimizer.batch_operations(operations, batch_size=2, delay_ms=50)
        
        # Wait for operations to complete
        time.sleep(0.3)
        
        # Check if all operations completed
        self.assertEqual(len(operations_completed), 5, "All operations should complete")
        
        execution_time = time.time() - start_time
        self.assertLess(execution_time, 0.5, f"Batch operations took too long: {execution_time:.3f}s")

if __name__ == '__main__':
    print("Testing startup performance optimizations...")
    unittest.main(verbosity=2)


