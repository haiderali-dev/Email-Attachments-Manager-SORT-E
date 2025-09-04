import time
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QProgressBar, QGroupBox, QTextEdit, QTabWidget, QWidget, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QSpinBox
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
from utils.performance_optimizer import performance_optimizer
from utils.ui_optimizer import ui_optimizer
from services.database_pool import db_pool

class PerformanceDashboard(QDialog):
    """Performance monitoring and optimization dashboard"""
    
    # Signals
    optimization_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚀 Performance Dashboard")
        self.setModal(False)
        self.resize(800, 600)
        
        # Setup UI
        self.init_ui()
        
        # Start monitoring
        self.start_monitoring()
        
        # Connect signals
        self.connect_signals()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_overview_tab()
        self.create_performance_tab()
        self.create_optimization_tab()
        self.create_database_tab()
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_all_metrics)
        
        self.optimize_btn = QPushButton("⚡ Force Optimization")
        self.optimize_btn.clicked.connect(self.force_optimization)
        
        self.export_btn = QPushButton("📊 Export Report")
        self.export_btn.clicked.connect(self.export_report)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.optimize_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def create_overview_tab(self):
        """Create the overview tab"""
        overview_widget = QWidget()
        layout = QVBoxLayout(overview_widget)
        
        # Performance score
        score_group = QGroupBox("🎯 Overall Performance Score")
        score_layout = QFormLayout(score_group)
        
        self.performance_score_label = QLabel("Calculating...")
        self.performance_score_label.setFont(QFont("Arial", 16, QFont.Bold))
        score_layout.addRow("Score:", self.performance_score_label)
        
        self.performance_bar = QProgressBar()
        self.performance_bar.setRange(0, 100)
        self.performance_bar.setFormat("%p%")
        score_layout.addRow("Progress:", self.performance_bar)
        
        layout.addWidget(score_group)
        
        # Quick stats
        stats_group = QGroupBox("📊 Quick Statistics")
        stats_layout = QGridLayout(stats_group)
        
        self.memory_label = QLabel("--")
        self.cpu_label = QLabel("--")
        self.cache_label = QLabel("--")
        self.ui_responsiveness_label = QLabel("--")
        
        stats_layout.addWidget(QLabel("Memory Usage:"), 0, 0)
        stats_layout.addWidget(self.memory_label, 0, 1)
        stats_layout.addWidget(QLabel("CPU Usage:"), 0, 2)
        stats_layout.addWidget(self.cpu_label, 0, 3)
        
        stats_layout.addWidget(QLabel("Cache Size:"), 1, 0)
        stats_layout.addWidget(self.cache_label, 1, 1)
        stats_layout.addWidget(QLabel("UI Responsiveness:"), 1, 2)
        stats_layout.addWidget(self.ui_responsiveness_label, 1, 3)
        
        layout.addWidget(stats_group)
        
        # Status
        status_group = QGroupBox("📈 Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        layout.addWidget(status_group)
        
        self.tab_widget.addTab(overview_widget, "Overview")
    
    def create_performance_tab(self):
        """Create the performance monitoring tab"""
        perf_widget = QWidget()
        layout = QVBoxLayout(perf_widget)
        
        # Memory usage
        memory_group = QGroupBox("💾 Memory Management")
        memory_layout = QFormLayout(memory_group)
        
        self.memory_usage_bar = QProgressBar()
        self.memory_usage_bar.setRange(0, 100)
        memory_layout.addRow("Usage:", self.memory_usage_bar)
        
        self.memory_available_label = QLabel("--")
        memory_layout.addRow("Available:", self.memory_available_label)
        
        self.gc_count_label = QLabel("--")
        memory_layout.addRow("GC Count:", self.gc_count_label)
        
        layout.addWidget(memory_group)
        
        # Cache performance
        cache_group = QGroupBox("🗄️ Cache Performance")
        cache_layout = QFormLayout(cache_group)
        
        self.cache_size_label = QLabel("--")
        cache_layout.addRow("Size:", self.cache_size_label)
        
        self.cache_hit_rate_label = QLabel("--")
        cache_layout.addRow("Hit Rate:", self.cache_hit_rate_label)
        
        self.cache_ttl_label = QLabel("--")
        cache_layout.addRow("TTL:", self.cache_ttl_label)
        
        layout.addWidget(cache_group)
        
        # UI responsiveness
        ui_group = QGroupBox("🎨 UI Responsiveness")
        ui_layout = QFormLayout(ui_group)
        
        self.ui_score_label = QLabel("--")
        ui_layout.addRow("Score:", self.ui_score_label)
        
        self.ui_update_times_label = QLabel("--")
        ui_layout.addRow("Update Times:", self.ui_update_times_label)
        
        self.registered_widgets_label = QLabel("--")
        ui_layout.addRow("Widgets:", self.registered_widgets_label)
        
        layout.addWidget(ui_group)
        
        layout.addStretch()
        self.tab_widget.addTab(perf_widget, "Performance")
    
    def create_optimization_tab(self):
        """Create the optimization control tab"""
        opt_widget = QWidget()
        layout = QVBoxLayout(opt_widget)
        
        # Optimization settings
        settings_group = QGroupBox("⚙️ Optimization Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.auto_optimize_checkbox = QCheckBox("Enable Auto-Optimization")
        self.auto_optimize_checkbox.setChecked(True)
        settings_layout.addRow(self.auto_optimize_checkbox)
        
        self.memory_threshold_spin = QSpinBox()
        self.memory_threshold_spin.setRange(50, 95)
        self.memory_threshold_spin.setValue(80)
        self.memory_threshold_spin.setSuffix("%")
        settings_layout.addRow("Memory Threshold:", self.memory_threshold_spin)
        
        self.gc_threshold_spin = QSpinBox()
        self.gc_threshold_spin.setRange(100, 10000)
        self.gc_threshold_spin.setValue(1000)
        self.gc_threshold_spin.setSuffix(" objects")
        settings_layout.addRow("GC Threshold:", self.gc_threshold_spin)
        
        layout.addWidget(settings_group)
        
        # Manual optimization
        manual_group = QGroupBox("🔧 Manual Optimization")
        manual_layout = QVBoxLayout(manual_group)
        
        self.optimize_memory_btn = QPushButton("🧹 Optimize Memory")
        self.optimize_memory_btn.clicked.connect(self.optimize_memory)
        
        self.optimize_cache_btn = QPushButton("🗑️ Clear Cache")
        self.optimize_cache_btn.clicked.connect(self.optimize_cache)
        
        self.optimize_ui_btn = QPushButton("🎨 Optimize UI")
        self.optimize_ui_btn.clicked.connect(self.optimize_ui)
        
        manual_layout.addWidget(self.optimize_memory_btn)
        manual_layout.addWidget(self.optimize_cache_btn)
        manual_layout.addWidget(self.optimize_ui_btn)
        
        layout.addWidget(manual_group)
        
        # Optimization history
        history_group = QGroupBox("📋 Optimization History")
        history_layout = QVBoxLayout(history_group)
        
        self.optimization_table = QTableWidget()
        self.optimization_table.setColumnCount(4)
        self.optimization_table.setHorizontalHeaderLabels([
            "Time", "Type", "Result", "Details"
        ])
        
        header = self.optimization_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        
        history_layout.addWidget(self.optimization_table)
        
        layout.addWidget(history_group)
        
        self.tab_widget.addTab(opt_widget, "Optimization")
    
    def create_database_tab(self):
        """Create the database performance tab"""
        db_widget = QWidget()
        layout = QVBoxLayout(db_widget)
        
        # Connection pool stats
        pool_group = QGroupBox("🔌 Connection Pool")
        pool_layout = QFormLayout(pool_group)
        
        self.pool_size_label = QLabel("--")
        pool_layout.addRow("Pool Size:", self.pool_size_label)
        
        self.active_connections_label = QLabel("--")
        pool_layout.addRow("Active Connections:", self.active_connections_label)
        
        self.pool_utilization_label = QLabel("--")
        pool_layout.addRow("Utilization:", self.pool_utilization_label)
        
        self.total_created_label = QLabel("--")
        pool_layout.addRow("Total Created:", self.total_created_label)
        
        layout.addWidget(pool_group)
        
        # Query performance
        query_group = QGroupBox("📊 Query Performance")
        query_layout = QFormLayout(query_group)
        
        self.total_queries_label = QLabel("--")
        query_layout.addRow("Total Queries:", self.total_queries_label)
        
        self.slow_queries_label = QLabel("--")
        query_layout.addRow("Slow Queries:", self.slow_queries_label)
        
        self.avg_query_time_label = QLabel("--")
        query_layout.addRow("Avg Query Time:", self.avg_query_time_label)
        
        layout.addWidget(query_group)
        
        # Database actions
        actions_group = QGroupBox("⚡ Database Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        self.optimize_db_btn = QPushButton("🔧 Optimize Database")
        self.optimize_db_btn.clicked.connect(self.optimize_database)
        
        self.clear_query_cache_btn = QPushButton("🗑️ Clear Query Cache")
        self.clear_query_cache_btn.clicked.connect(self.clear_query_cache)
        
        actions_layout.addWidget(self.optimize_db_btn)
        actions_layout.addWidget(self.clear_query_cache_btn)
        
        layout.addWidget(actions_group)
        
        layout.addStretch()
        self.tab_widget.addTab(db_widget, "Database")
    
    def connect_signals(self):
        """Connect performance optimizer signals"""
        try:
            performance_optimizer.performance_warning.connect(self.on_performance_warning)
            performance_optimizer.optimization_completed.connect(self.on_optimization_completed)
        except:
            pass
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_metrics)
        self.monitor_timer.start(1000)  # Update every second
        
        # Initial update
        self.update_metrics()
    
    def update_metrics(self):
        """Update all performance metrics"""
        try:
            # Get performance stats
            perf_stats = performance_optimizer.get_performance_stats()
            ui_stats = ui_optimizer.get_optimization_stats()
            db_stats = db_pool.get_pool_stats()
            
            # Update overview
            self.update_overview_metrics(perf_stats, ui_stats, db_stats)
            
            # Update performance tab
            self.update_performance_metrics(perf_stats, ui_stats)
            
            # Update database tab
            self.update_database_metrics(db_stats)
            
        except Exception as e:
            print(f"Metrics update error: {e}")
    
    def update_overview_metrics(self, perf_stats, ui_stats, db_stats):
        """Update overview tab metrics"""
        try:
            # Calculate performance score
            memory_score = max(0, 100 - perf_stats.get('memory_usage_percent', 0))
            ui_score = perf_stats.get('ui_responsiveness', 100)
            cache_score = min(100, perf_stats.get('cache_hit_rate', 0))
            
            overall_score = (memory_score + ui_score + cache_score) / 3
            self.performance_score_label.setText(f"{overall_score:.1f}/100")
            self.performance_bar.setValue(int(overall_score))
            
            # Update quick stats
            self.memory_label.setText(f"{perf_stats.get('memory_usage_percent', 0):.1f}%")
            self.cpu_label.setText(f"{perf_stats.get('cpu_percent', 0):.1f}%")
            self.cache_label.setText(f"{perf_stats.get('cache_size', 0)} items")
            self.ui_responsiveness_label.setText(f"{ui_score:.1f}/100")
            
        except Exception as e:
            print(f"Overview update error: {e}")
    
    def update_performance_metrics(self, perf_stats, ui_stats):
        """Update performance tab metrics"""
        try:
            # Memory
            memory_percent = perf_stats.get('memory_usage_percent', 0)
            self.memory_usage_bar.setValue(int(memory_percent))
            self.memory_available_label.setText(f"{perf_stats.get('memory_available_gb', 0)} GB")
            self.gc_count_label.setText(str(perf_stats.get('garbage_collection_count', 0)))
            
            # Cache
            self.cache_size_label.setText(f"{perf_stats.get('cache_size', 0)} items")
            self.cache_hit_rate_label.setText(f"{perf_stats.get('cache_hit_rate', 0):.1f}%")
            self.cache_ttl_label.setText("5 min")
            
            # UI
            ui_score = perf_stats.get('ui_responsiveness', 100)
            self.ui_score_label.setText(f"{ui_score:.1f}/100")
            self.ui_update_times_label.setText(f"{len(perf_stats.get('ui_update_times', []))} samples")
            self.registered_widgets_label.setText(str(ui_stats.get('registered_widgets', 0)))
            
        except Exception as e:
            print(f"Performance update error: {e}")
    
    def update_database_metrics(self, db_stats):
        """Update database tab metrics"""
        try:
            self.pool_size_label.setText(str(db_stats.get('pool_size', 0)))
            self.active_connections_label.setText(str(db_stats.get('active_connections', 0)))
            self.pool_utilization_label.setText(f"{db_stats.get('pool_utilization', 0):.1f}%")
            self.total_created_label.setText(str(db_stats.get('total_created', 0)))
            
        except Exception as e:
            print(f"Database update error: {e}")
    
    def refresh_all_metrics(self):
        """Refresh all performance metrics"""
        self.update_metrics()
        self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Manual refresh completed")
    
    def force_optimization(self):
        """Force immediate optimization"""
        try:
            performance_optimizer.force_optimization()
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Forced optimization started")
        except Exception as e:
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Optimization error: {e}")
    
    def optimize_memory(self):
        """Optimize memory usage"""
        try:
            import gc
            collected = gc.collect()
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Memory optimization: cleaned {collected} objects")
        except Exception as e:
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Memory optimization error: {e}")
    
    def optimize_cache(self):
        """Optimize cache"""
        try:
            # Clear old cache entries
            performance_optimizer._cleanup_cache()
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Cache optimization completed")
        except Exception as e:
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Cache optimization error: {e}")
    
    def optimize_ui(self):
        """Optimize UI performance"""
        try:
            # Force UI optimization
            ui_optimizer._optimize_widgets()
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] UI optimization completed")
        except Exception as e:
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] UI optimization error: {e}")
    
    def optimize_database(self):
        """Optimize database performance"""
        try:
            # Get database stats
            stats = db_pool.get_pool_stats()
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Database optimization: {stats.get('pool_utilization', 0):.1f}% utilization")
        except Exception as e:
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Database optimization error: {e}")
    
    def clear_query_cache(self):
        """Clear query cache"""
        try:
            # Clear query cache
            performance_optimizer.query_cache.clear()
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Query cache cleared")
        except Exception as e:
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Query cache clear error: {e}")
    
    def export_report(self):
        """Export performance report"""
        try:
            # Generate report
            report = self.generate_performance_report()
            
            # Save to file
            filename = f"performance_report_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w') as f:
                f.write(report)
            
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Report exported to {filename}")
        except Exception as e:
            self.status_text.append(f"[{time.strftime('%H:%M:%S')}] Export error: {e}")
    
    def generate_performance_report(self):
        """Generate performance report"""
        try:
            perf_stats = performance_optimizer.get_performance_stats()
            ui_stats = ui_optimizer.get_optimization_stats()
            db_stats = db_pool.get_pool_stats()
            
            report = f"""
Performance Report - {time.strftime('%Y-%m-%d %H:%M:%S')}
{'='*50}

OVERVIEW:
- Memory Usage: {perf_stats.get('memory_usage_percent', 0):.1f}%
- UI Responsiveness: {perf_stats.get('ui_responsiveness', 0):.1f}/100
- Cache Hit Rate: {perf_stats.get('cache_hit_rate', 0):.1f}%
- Active Threads: {perf_stats.get('active_threads', 0)}

UI OPTIMIZATION:
- Registered Widgets: {ui_stats.get('registered_widgets', 0)}
- Active Timers: {ui_stats.get('active_timers', 0)}
- Pending Batches: {ui_stats.get('pending_batches', 0)}

DATABASE:
- Pool Size: {db_stats.get('pool_size', 0)}
- Active Connections: {db_stats.get('active_connections', 0)}
- Pool Utilization: {db_stats.get('pool_utilization', 0):.1f}%
- Total Created: {db_stats.get('total_created', 0)}

OPTIMIZATION HISTORY:
"""
            
            for opt in ui_stats.get('optimization_history', [])[:10]:
                report += f"- {opt['widget_type']}: {opt['action']} at {time.strftime('%H:%M:%S', time.localtime(opt['timestamp']))}\n"
            
            return report
            
        except Exception as e:
            return f"Error generating report: {e}"
    
    def on_performance_warning(self, level, message):
        """Handle performance warnings"""
        self.status_text.append(f"[{time.strftime('%H:%M:%S')}] {level.upper()}: {message}")
    
    def on_optimization_completed(self, optimization_type):
        """Handle optimization completion"""
        self.status_text.append(f"[{time.strftime('%H:%M:%S')}] {optimization_type} completed")
    
    def closeEvent(self, event):
        """Handle dialog closing"""
        if hasattr(self, 'monitor_timer'):
            self.monitor_timer.stop()
        event.accept()
