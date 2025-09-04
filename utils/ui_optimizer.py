import time
import threading
from typing import Callable, Any, Optional, Dict, List
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QObject, QEvent, Qt
from PyQt5.QtWidgets import QApplication, QWidget, QListWidget, QTableWidget, QTreeWidget
from PyQt5.QtGui import QPainter, QPalette, QColor
from utils.performance_optimizer import performance_optimizer

class UIOptimizer(QObject):
    """UI optimization system for improved responsiveness"""
    
    # Signals
    optimization_started = pyqtSignal(str)
    optimization_completed = pyqtSignal(str)
    performance_warning = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.optimization_active = False
        self.widget_cache = {}
        self.update_timers = {}
        self.batch_updates = {}
        
        # Performance thresholds
        self.max_items_per_widget = 1000
        self.max_rows_per_table = 500
        self.max_tree_items = 300
        self.update_batch_size = 50
        self.update_delay_ms = 16  # ~60 FPS
        
        # Start optimization
        self.start_optimization()
    
    def start_optimization(self):
        """Start UI optimization system"""
        self.optimization_active = True
        
        # Start background optimization thread
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
    
    def stop_optimization(self):
        """Stop UI optimization"""
        self.optimization_active = False
        if hasattr(self, 'optimization_thread'):
            self.optimization_thread.join(timeout=1)
    
    def _optimization_loop(self):
        """Background optimization loop"""
        while self.optimization_active:
            try:
                # Optimize widget performance
                self._optimize_widgets()
                
                # Clean up expired timers
                self._cleanup_timers()
                
                # Process batch updates
                self._process_batch_updates()
                
                time.sleep(5)  # Run every 5 seconds
                
            except Exception as e:
                print(f"UI optimization error: {e}")
    
    def _optimize_widgets(self):
        """Optimize widget performance"""
        for widget_id, widget_info in self.widget_cache.items():
            try:
                widget = widget_info.get('widget')
                if widget and widget.isVisible():
                    self._optimize_single_widget(widget)
            except Exception as e:
                print(f"Widget optimization error: {e}")
    
    def _optimize_single_widget(self, widget: QWidget):
        """Optimize a single widget"""
        if isinstance(widget, QListWidget):
            self._optimize_list_widget(widget)
        elif isinstance(widget, QTableWidget):
            self._optimize_table_widget(widget)
        elif isinstance(widget, QTreeWidget):
            self._optimize_tree_widget(widget)
    
    def _optimize_list_widget(self, list_widget: QListWidget):
        """Optimize list widget performance"""
        if list_widget.count() > self.max_items_per_widget:
            # Remove old items to maintain performance
            items_to_remove = list_widget.count() - self.max_items_per_widget
            for _ in range(items_to_remove):
                list_widget.takeItem(0)
            
            # Update widget info
            self._update_widget_info(list_widget, 'items_removed', items_to_remove)
    
    def _optimize_table_widget(self, table_widget: QTableWidget):
        """Optimize table widget performance"""
        if table_widget.rowCount() > self.max_rows_per_table:
            # Remove old rows to maintain performance
            rows_to_remove = table_widget.rowCount() - self.max_rows_per_table
            table_widget.setRowCount(self.max_rows_per_table)
            
            # Update widget info
            self._update_widget_info(table_widget, 'rows_removed', rows_to_remove)
    
    def _optimize_tree_widget(self, tree_widget: QTreeWidget):
        """Optimize tree widget performance"""
        # Count total items
        total_items = 0
        root = tree_widget.invisibleRootItem()
        
        def count_items(item):
            nonlocal total_items
            total_items += 1
            for i in range(item.childCount()):
                count_items(item.child(i))
        
        count_items(root)
        
        if total_items > self.max_tree_items:
            # Collapse all items to improve performance
            tree_widget.collapseAll()
            
            # Update widget info
            self._update_widget_info(tree_widget, 'collapsed', True)
    
    def _update_widget_info(self, widget: QWidget, action: str, value: Any):
        """Update widget optimization info"""
        widget_id = id(widget)
        if widget_id in self.widget_cache:
            self.widget_cache[widget_id]['last_optimization'] = {
                'action': action,
                'value': value,
                'timestamp': time.time()
            }
    
    def _cleanup_timers(self):
        """Clean up expired update timers"""
        current_time = time.time()
        expired_timers = []
        
        for timer_id, timer_info in self.update_timers.items():
            if current_time - timer_info['last_used'] > 300:  # 5 minutes
                expired_timers.append(timer_id)
        
        for timer_id in expired_timers:
            del self.update_timers[timer_id]
    
    def _process_batch_updates(self):
        """Process pending batch updates"""
        current_time = time.time()
        completed_batches = []
        
        for batch_id, batch_info in self.batch_updates.items():
            if current_time >= batch_info['execute_at']:
                try:
                    self._execute_batch_update(batch_info)
                    completed_batches.append(batch_id)
                except Exception as e:
                    print(f"Batch update error: {e}")
                    completed_batches.append(batch_id)
        
        # Remove completed batches
        for batch_id in completed_batches:
            del self.batch_updates[batch_id]
    
    def _execute_batch_update(self, batch_info: Dict[str, Any]):
        """Execute a batch update"""
        widget = batch_info['widget']
        updates = batch_info['updates']
        
        # Suspend visual updates
        widget.setUpdatesEnabled(False)
        
        try:
            # Apply updates
            for update_func, args, kwargs in updates:
                update_func(*args, **kwargs)
            
            # Force update
            widget.update()
            
        finally:
            # Resume visual updates
            widget.setUpdatesEnabled(True)
    
    def register_widget(self, widget: QWidget, widget_type: str = 'generic'):
        """Register a widget for optimization"""
        widget_id = id(widget)
        self.widget_cache[widget_id] = {
            'widget': widget,
            'type': widget_type,
            'registered_at': time.time(),
            'last_optimization': None,
            'update_count': 0
        }
    
    def unregister_widget(self, widget: QWidget):
        """Unregister a widget from optimization"""
        widget_id = id(widget)
        if widget_id in self.widget_cache:
            del self.widget_cache[widget_id]
    
    def defer_update(self, widget: QWidget, update_func: Callable, *args, **kwargs):
        """Defer a widget update to avoid blocking the UI"""
        widget_id = id(widget)
        
        if widget_id not in self.update_timers:
            # Create new timer for this widget
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._execute_deferred_update(widget_id))
            
            self.update_timers[widget_id] = {
                'timer': timer,
                'last_used': time.time(),
                'pending_updates': []
            }
        
        # Add update to pending list
        self.update_timers[widget_id]['pending_updates'].append((update_func, args, kwargs))
        self.update_timers[widget_id]['last_used'] = time.time()
        
        # Start timer if not already running
        timer = self.update_timers[widget_id]['timer']
        if not timer.isActive():
            timer.start(self.update_delay_ms)
    
    def _execute_deferred_update(self, widget_id: int):
        """Execute deferred updates for a widget"""
        if widget_id not in self.update_timers:
            return
        
        timer_info = self.update_timers[widget_id]
        updates = timer_info['pending_updates']
        timer_info['pending_updates'] = []
        
        # Execute all pending updates
        for update_func, args, kwargs in updates:
            try:
                update_func(*args, **kwargs)
            except Exception as e:
                print(f"Deferred update error: {e}")
    
    def batch_update(self, widget: QWidget, updates: List[tuple], delay_ms: int = 0):
        """Schedule a batch update for a widget"""
        batch_id = f"batch_{id(widget)}_{int(time.time())}"
        
        self.batch_updates[batch_id] = {
            'widget': widget,
            'updates': updates,
            'execute_at': time.time() + (delay_ms / 1000.0),
            'created_at': time.time()
        }
    
    def optimize_rendering(self, widget: QWidget):
        """Optimize widget rendering performance"""
        # Set rendering hints for better performance
        widget.setAttribute(Qt.WA_OpaquePaintEvent, True)
        widget.setAttribute(Qt.WA_NoSystemBackground, True)
        
        # Optimize palette for performance
        palette = widget.palette()
        palette.setColor(QPalette.Window, QColor(255, 255, 255))
        widget.setPalette(palette)
        
        # Register for optimization
        self.register_widget(widget, 'rendering_optimized')
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get UI optimization statistics"""
        return {
            'registered_widgets': len(self.widget_cache),
            'active_timers': len(self.update_timers),
            'pending_batches': len(self.batch_updates),
            'widget_types': self._get_widget_type_stats(),
            'optimization_history': self._get_optimization_history()
        }
    
    def _get_widget_type_stats(self) -> Dict[str, int]:
        """Get statistics by widget type"""
        stats = {}
        for widget_info in self.widget_cache.values():
            widget_type = widget_info['type']
            stats[widget_type] = stats.get(widget_type, 0) + 1
        return stats
    
    def _get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get recent optimization history"""
        history = []
        for widget_info in self.widget_cache.values():
            if widget_info['last_optimization']:
                history.append({
                    'widget_type': widget_info['type'],
                    'action': widget_info['last_optimization']['action'],
                    'timestamp': widget_info['last_optimization']['timestamp']
                })
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        return history[:20]  # Return last 20 optimizations

# Global UI optimizer instance
ui_optimizer = UIOptimizer()

# Utility functions for easy UI optimization
def optimize_widget(widget: QWidget):
    """Optimize a widget for better performance"""
    ui_optimizer.optimize_rendering(widget)

def defer_widget_update(widget: QWidget, update_func: Callable, *args, **kwargs):
    """Defer a widget update to avoid blocking the UI"""
    ui_optimizer.defer_update(widget, update_func, *args, **kwargs)

def batch_widget_updates(widget: QWidget, updates: List[tuple], delay_ms: int = 0):
    """Schedule batch updates for a widget"""
    ui_optimizer.batch_update(widget, updates, delay_ms)
