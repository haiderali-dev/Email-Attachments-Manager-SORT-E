import time
import threading
from typing import Callable, Any, Optional, Dict, List
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication
from utils.performance_optimizer import performance_optimizer

class AsyncWorker(QObject):
    """High-performance async worker for heavy operations"""
    
    # Signals
    started = pyqtSignal()
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # current, total
    status = pyqtSignal(str)  # status message
    
    def __init__(self, operation: Callable, *args, **kwargs):
        super().__init__()
        self.operation = operation
        self.args = args
        self.kwargs = kwargs
        self.thread = QThread()
        self.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(self.run_operation)
        self.finished.connect(self.thread.quit)
        self.error.connect(self.thread.quit)
        
        # Performance tracking
        self.start_time = None
        self.operation_id = f"{operation.__name__}_{int(time.time())}"
    
    def start(self):
        """Start the worker thread"""
        self.start_time = time.time()
        self.started.emit()
        self.thread.start()
    
    def stop(self):
        """Stop the worker thread"""
        self.thread.quit()
        self.thread.wait(5000)  # Wait up to 5 seconds
    
    def run_operation(self):
        """Run the operation in the background thread"""
        try:
            # Measure performance
            start_time = time.time()
            
            # Run the operation
            result = self.operation(*self.args, **self.kwargs)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log performance metrics
            performance_optimizer.cache_result(
                f"operation_{self.operation_id}",
                {
                    'execution_time': execution_time,
                    'success': True,
                    'timestamp': time.time()
                },
                ttl=3600  # 1 hour
            )
            
            # Emit result
            self.finished.emit(result)
            
        except Exception as e:
            # Log error
            performance_optimizer.cache_result(
                f"operation_{self.operation_id}",
                {
                    'execution_time': time.time() - self.start_time if self.start_time else 0,
                    'success': False,
                    'error': str(e),
                    'timestamp': time.time()
                },
                ttl=3600  # 1 hour
            )
            
            self.error.emit(str(e))

class BatchWorker(QObject):
    """Worker for processing operations in batches"""
    
    # Signals
    batch_progress = pyqtSignal(int, int)  # current_batch, total_batches
    item_progress = pyqtSignal(int, int)   # current_item, total_items
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, operations: List[Callable], batch_size: int = 10, delay_ms: int = 50):
        super().__init__()
        self.operations = operations
        self.batch_size = batch_size
        self.delay_ms = delay_ms
        self.results = []
        self.current_batch = 0
        self.total_batches = (len(operations) + batch_size - 1) // batch_size
        
        # Performance tracking
        self.start_time = time.time()
    
    def start(self):
        """Start batch processing"""
        self.start_time = time.time()
        self._process_next_batch()
    
    def _process_next_batch(self):
        """Process the next batch of operations"""
        if self.current_batch >= self.total_batches:
            # All batches completed
            execution_time = time.time() - self.start_time
            performance_optimizer.cache_result(
                f"batch_operation_{int(time.time())}",
                {
                    'total_operations': len(self.operations),
                    'batch_size': self.batch_size,
                    'execution_time': execution_time,
                    'success': True
                },
                ttl=3600
            )
            self.finished.emit(self.results)
            return
        
        start_idx = self.current_batch * self.batch_size
        end_idx = min(start_idx + self.batch_size, len(self.operations))
        current_batch_ops = self.operations[start_idx:end_idx]
        
        # Process current batch
        for i, operation in enumerate(current_batch_ops):
            try:
                result = operation()
                self.results.append(result)
                self.item_progress.emit(start_idx + i + 1, len(self.operations))
            except Exception as e:
                print(f"Batch operation error: {e}")
                self.results.append(None)
        
        self.batch_progress.emit(self.current_batch + 1, self.total_batches)
        self.current_batch += 1
        
        # Schedule next batch
        QTimer.singleShot(self.delay_ms, self._process_next_batch)

class LazyLoader(QObject):
    """Lazy loading system for UI components"""
    
    # Signals
    loading_started = pyqtSignal()
    loading_finished = pyqtSignal()
    progress = pyqtSignal(int)
    
    def __init__(self, load_function: Callable, trigger_condition: Callable = None):
        super().__init__()
        self.load_function = load_function
        self.trigger_condition = trigger_condition
        self.loaded = False
        self.loading = False
        self.worker = None
    
    def trigger_load(self, *args, **kwargs):
        """Trigger lazy loading if conditions are met"""
        if self.loaded or self.loading:
            return
        
        if self.trigger_condition and not self.trigger_condition(*args, **kwargs):
            return
        
        self.loading = True
        self.loading_started.emit()
        
        # Create worker for loading
        self.worker = AsyncWorker(self.load_function, *args, **kwargs)
        self.worker.finished.connect(self._on_load_complete)
        self.worker.error.connect(self._on_load_error)
        self.worker.start()
    
    def _on_load_complete(self, result):
        """Handle load completion"""
        self.loaded = True
        self.loading = False
        self.loading_finished.emit()
    
    def _on_load_error(self, error):
        """Handle load error"""
        self.loading = False
        print(f"Lazy loading error: {error}")

class PerformanceWorker(QObject):
    """Worker for performance optimization tasks"""
    
    # Signals
    optimization_started = pyqtSignal(str)
    optimization_completed = pyqtSignal(str, dict)
    optimization_error = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.thread = QThread()
        self.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(self._run_optimization_loop)
        self.optimization_started.connect(self.thread.quit)
    
    def start(self):
        """Start performance optimization worker"""
        self.thread.start()
    
    def stop(self):
        """Stop performance optimization worker"""
        self.thread.quit()
        self.thread.wait()
    
    def _run_optimization_loop(self):
        """Run performance optimization loop"""
        try:
            # Force optimization
            performance_optimizer.force_optimization()
            
            # Get performance stats
            stats = performance_optimizer.get_performance_stats()
            
            self.optimization_completed.emit("Performance optimization", stats)
            
        except Exception as e:
            self.optimization_error.emit("Performance optimization", str(e))

# Utility functions for easy async operations
def run_async(operation: Callable, *args, **kwargs) -> AsyncWorker:
    """Run an operation asynchronously"""
    worker = AsyncWorker(operation, *args, **kwargs)
    worker.start()
    return worker

def run_batch(operations: List[Callable], batch_size: int = 10) -> BatchWorker:
    """Run operations in batches"""
    worker = BatchWorker(operations, batch_size)
    worker.start()
    return worker

def lazy_load(load_function: Callable, trigger_condition: Callable = None) -> LazyLoader:
    """Create a lazy loader"""
    return LazyLoader(load_function, trigger_condition)
