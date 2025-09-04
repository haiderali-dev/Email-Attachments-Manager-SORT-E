from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QCheckBox, QSpinBox, QLabel
)
from config.settings import CONFIG, save_config

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings")
        self.setModal(True)
        self.resize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # Session settings
        session_group = QGroupBox("Session Settings")
        session_layout = QFormLayout(session_group)
        
        self.session_days = QSpinBox()
        self.session_days.setRange(1, 365)
        self.session_days.setValue(CONFIG.get('session_days', 90))
        self.session_days.setSuffix(" days")
        
        session_layout.addRow("Email Session Duration:", self.session_days)
        
        layout.addWidget(session_group)
        
        # Default settings
        defaults_group = QGroupBox("Default Settings")
        defaults_layout = QFormLayout(defaults_group)
        
        self.default_imap = QLineEdit()
        self.default_imap.setText(CONFIG.get('default_imap_host', 'mail2.multinet.com.pk'))
        
        defaults_layout.addRow("Default IMAP Host:", self.default_imap)
        
        layout.addWidget(defaults_group)
        
        # Real-time monitoring settings
        monitoring_group = QGroupBox("Real-Time Monitoring")
        monitoring_layout = QFormLayout(monitoring_group)
        
        self.real_time_monitoring = QCheckBox("Enable real-time email monitoring")
        self.real_time_monitoring.setChecked(CONFIG.get('real_time_monitoring', True))
        self.real_time_monitoring.setToolTip(
            "When enabled, the application will automatically check for new emails\n"
            "at regular intervals while running. This ensures you get new emails\n"
            "without manual syncing."
        )
        
        self.monitoring_interval = QSpinBox()
        self.monitoring_interval.setRange(60, 3600)  # 1 minute to 1 hour
        self.monitoring_interval.setValue(CONFIG.get('monitoring_interval', 300))
        self.monitoring_interval.setSuffix(" seconds")
        self.monitoring_interval.setToolTip(
            "How often to check for new emails (in seconds).\n"
            "Lower values provide faster updates but use more resources."
        )
        
        monitoring_layout.addRow("", self.real_time_monitoring)
        monitoring_layout.addRow("Check Interval:", self.monitoring_interval)
        
        # Add help text
        monitoring_help = QLabel(
            "<small><i>Real-time monitoring automatically fetches new emails that arrive\n"
            "while the application is running. Old emails are only fetched during manual sync.</i></small>"
        )
        monitoring_help.setWordWrap(True)
        monitoring_help.setStyleSheet("color: #666666; margin: 5px;")
        monitoring_layout.addRow("", monitoring_help)
        
        layout.addWidget(monitoring_group)
        
        # Add help text about automatic performance optimization
        performance_help = QLabel(
            "<small><i>💡 Performance is automatically optimized for high-speed email fetching.\n"
            "The system uses intelligent batching and progressive loading to handle\n"
            "large email volumes efficiently while maintaining UI responsiveness.</i></small>"
        )
        performance_help.setWordWrap(True)
        performance_help.setStyleSheet("color: #666666; margin: 10px; padding: 10px; background-color: #f0f8ff; border-radius: 5px;")
        layout.addWidget(performance_help)
        
                # Buttons
        button_layout = QHBoxLayout()

        # Save Settings button (blue)
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setDefault(True)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3182ce;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2a4365;
            }
            QPushButton:pressed {
                background-color: #1e3250;
            }
        """)

        # Cancel button (red)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e53e3e;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c53030;
            }
            QPushButton:pressed {
                background-color: #9b2c2c;
            }
        """)

        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
    def save_settings(self):
        """Save settings to config file"""
        global CONFIG
        
        CONFIG['session_days'] = self.session_days.value()
        CONFIG['default_imap_host'] = self.default_imap.text().strip()
        CONFIG['real_time_monitoring'] = self.real_time_monitoring.isChecked()
        CONFIG['monitoring_interval'] = self.monitoring_interval.value()
        
        save_config(CONFIG)
        
        QMessageBox.information(self, "Settings Saved", 
                              "Settings have been saved successfully!")
        self.accept()