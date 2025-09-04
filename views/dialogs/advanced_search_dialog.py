import mysql.connector
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QLabel, QGroupBox, QComboBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
from config.database import DB_CONFIG

class AdvancedSearchDialog(QtWidgets.QDialog):
    def __init__(self, parent, account_id):
        super().__init__(parent)
        self.account_id = account_id
        self.setWindowTitle("Advanced Email Search")
        self.setModal(True)
        self.resize(700, 600)
        
        layout = QVBoxLayout(self)
        
        # Search criteria
        criteria_group = QGroupBox("Search Criteria")
        criteria_layout = QFormLayout(criteria_group)
        
        self.sender_edit = QLineEdit()
        self.subject_edit = QLineEdit()
        self.body_edit = QLineEdit()
        
        self.date_from = QtWidgets.QDateEdit()
        self.date_from.setDate(QtCore.QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        
        self.date_to = QtWidgets.QDateEdit()
        self.date_to.setDate(QtCore.QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Read", "Unread", "With Attachments"])
        
        criteria_layout.addRow("Sender contains:", self.sender_edit)
        criteria_layout.addRow("Subject contains:", self.subject_edit)
        criteria_layout.addRow("Body contains:", self.body_edit)
        criteria_layout.addRow("Date from:", self.date_from)
        criteria_layout.addRow("Date to:", self.date_to)
        criteria_layout.addRow("Status:", self.status_combo)
        
        layout.addWidget(criteria_group)
        
        # Results
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_list = QListWidget()
        results_layout.addWidget(self.results_list)
        
        self.results_count = QLabel("0 results")
        self.results_count.setAlignment(Qt.AlignCenter)
        results_layout.addWidget(self.results_count)
        
        layout.addWidget(results_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        search_btn = QPushButton("🔍Search")
        search_btn.clicked.connect(self.perform_search)
        search_btn.setDefault(True)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_search)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        # Apply styles
        search_btn.setStyleSheet("""
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

        clear_btn.setStyleSheet(search_btn.styleSheet())  # same blue style

        close_btn.setStyleSheet("""
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
        
        btn_layout.addWidget(search_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)

    def perform_search(self):
        """Perform the advanced search"""
        if not self.account_id:
            return
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT id, subject, sender, date, read_status, has_attachment
                FROM emails
                WHERE account_id = %s
            """
            params = [self.account_id]
            
            # Add search conditions
            if self.sender_edit.text().strip():
                query += " AND sender LIKE %s"
                params.append(f"%{self.sender_edit.text().strip()}%")
            
            if self.subject_edit.text().strip():
                query += " AND subject LIKE %s"
                params.append(f"%{self.subject_edit.text().strip()}%")
            
            if self.body_edit.text().strip():
                query += " AND body LIKE %s"
                params.append(f"%{self.body_edit.text().strip()}%")
            
            # Date range
            query += " AND date BETWEEN %s AND %s"
            params.append(self.date_from.date().toPyDate())
            params.append(self.date_to.date().toPyDate())
            
            # Status filter
            status = self.status_combo.currentText()
            if status == "Read":
                query += " AND read_status = TRUE"
            elif status == "Unread":
                query += " AND read_status = FALSE"
            elif status == "With Attachments":
                query += " AND has_attachment = TRUE"
            
            query += " ORDER BY date DESC LIMIT 100"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Display results
            self.results_list.clear()
            for email_id, subject, sender, date, read_status, has_attachment in results:
                status_icon = "📖" if read_status else "📧"
                attachment_icon = "📎" if has_attachment else ""
                date_str = date.strftime("%Y-%m-%d %H:%M") if date else ""
                
                item_text = f"{status_icon} {attachment_icon} [{date_str}] {subject[:60]}{'...' if len(subject) > 60 else ''}\n    From: {sender}"
                
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(Qt.UserRole, email_id)
                self.results_list.addItem(item)
            
            self.results_count.setText(f"{len(results)} results")
            
        finally:
            cursor.close()
            conn.close()

    def clear_search(self):
        """Clear search criteria"""
        self.sender_edit.clear()
        self.subject_edit.clear()
        self.body_edit.clear()
        self.date_from.setDate(QtCore.QDate.currentDate().addDays(-30))
        self.date_to.setDate(QtCore.QDate.currentDate())
        self.status_combo.setCurrentText("All")
        self.results_list.clear()
        self.results_count.setText("0 results")