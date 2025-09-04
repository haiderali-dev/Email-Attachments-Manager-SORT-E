from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QCheckBox, QSpinBox, QLabel,
    QRadioButton, QButtonGroup, QDateEdit
)
from PyQt5.QtCore import Qt, QDate
from datetime import datetime, timedelta

class SyncDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🔄 Sync Emails")
        self.setModal(True)
        self.resize(400, 300)
        
        self.sync_type = None
        self.custom_date = None
        
        layout = QVBoxLayout(self)
        
        # Sync options
        sync_group = QGroupBox("📅 Sync Options")
        sync_layout = QVBoxLayout(sync_group)
        
        # Create button group for radio buttons
        self.button_group = QButtonGroup()
        
        # Today option
        self.today_radio = QRadioButton("📅 Today")
        self.today_radio.setToolTip("Fetch emails from today only")
        self.button_group.addButton(self.today_radio)
        sync_layout.addWidget(self.today_radio)
        
        # Weekly option
        self.weekly_radio = QRadioButton("📅 Weekly")
        self.weekly_radio.setToolTip("Fetch emails from the last 7 days")
        self.button_group.addButton(self.weekly_radio)
        sync_layout.addWidget(self.weekly_radio)
        
        # Monthly option
        self.monthly_radio = QRadioButton("📅 Monthly")
        self.monthly_radio.setToolTip("Fetch emails from the last 30 days")
        self.button_group.addButton(self.monthly_radio)
        sync_layout.addWidget(self.monthly_radio)
        
        # Custom Date option
        self.custom_radio = QRadioButton("📅 Custom Date")
        self.custom_radio.setToolTip("Fetch emails from a specific date to now")
        self.button_group.addButton(self.custom_radio)
        sync_layout.addWidget(self.custom_radio)
        
        # Custom date picker
        self.custom_date_picker = QDateEdit()
        self.custom_date_picker.setCalendarPopup(True)
        self.custom_date_picker.setDate(QDate.currentDate())
        self.custom_date_picker.setEnabled(False)
        self.custom_date_picker.setToolTip("Select the start date for custom sync")
        
        custom_date_layout = QHBoxLayout()
        custom_date_layout.addWidget(QLabel("From:"))
        custom_date_layout.addWidget(self.custom_date_picker)
        custom_date_layout.addStretch()
        sync_layout.addLayout(custom_date_layout)
        
        # Connect radio button to enable/disable date picker
        self.custom_radio.toggled.connect(self.custom_date_picker.setEnabled)
        
        layout.addWidget(sync_group)
        
        # Help text
        help_label = QLabel(
            "<small><i>📋 <b>Sync fetches ALL emails within the selected time period</b><br>"
            "This sync option will fetch ALL emails from the specified time period using progressive loading "
            "to maintain application performance. The application will remain responsive and show emails "
            "as they are fetched. New emails that arrive while the application is running are automatically "
            "fetched by real-time monitoring.</i></small>"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666666; margin: 5px;")
        layout.addWidget(help_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
            # Sync button (blue)
        sync_btn = QPushButton("Sync")
        sync_btn.clicked.connect(self.accept_sync)
        sync_btn.setDefault(True)
        sync_btn.setStyleSheet("""
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
                
        btn_layout.addStretch()
        btn_layout.addWidget(sync_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Set default selection
        self.today_radio.setChecked(True)

    def accept_sync(self):
        """Handle sync button click"""
        if self.today_radio.isChecked():
            self.sync_type = "today"
        elif self.weekly_radio.isChecked():
            self.sync_type = "weekly"
        elif self.monthly_radio.isChecked():
            self.sync_type = "monthly"
        elif self.custom_radio.isChecked():
            self.sync_type = "custom"
            self.custom_date = self.custom_date_picker.date().toPyDate()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a sync option.")
            return
            
        self.accept()
        
    def get_sync_info(self):
        """Get sync information for the selected option"""
        # Determine sync type based on radio button state
        if self.today_radio.isChecked():
            sync_type = "today"
        elif self.weekly_radio.isChecked():
            sync_type = "weekly"
        elif self.monthly_radio.isChecked():
            sync_type = "monthly"
        elif self.custom_radio.isChecked():
            sync_type = "custom"
        else:
            return None
            
        if sync_type == "today":
            start_date = datetime.now().date()
            return {
                'type': 'today',
                'start_date': start_date,
                'description': f"Today ({start_date.strftime('%Y-%m-%d')})"
            }
        elif sync_type == "weekly":
            start_date = datetime.now().date() - timedelta(days=7)
            return {
                'type': 'weekly',
                'start_date': start_date,
                'description': f"Last 7 days (from {start_date.strftime('%Y-%m-%d')})"
            }
        elif sync_type == "monthly":
            start_date = datetime.now().date() - timedelta(days=30)
            return {
                'type': 'monthly',
                'start_date': start_date,
                'description': f"Last 30 days (from {start_date.strftime('%Y-%m-%d')})"
            }
        elif sync_type == "custom":
            custom_date = self.custom_date_picker.date().toPyDate()
            return {
                'type': 'custom',
                'start_date': custom_date,
                'description': f"Custom (from {custom_date.strftime('%Y-%m-%d')})"
            }
        else:
            return None


