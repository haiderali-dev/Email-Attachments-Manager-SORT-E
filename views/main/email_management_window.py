import datetime
import mysql.connector
import re
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QMessageBox, QCheckBox, QLabel,
    QSplitter, QListWidget, QTextEdit, QTextBrowser, QComboBox, QSpinBox, QTreeWidget,
    QTreeWidgetItem, QTabWidget, QGroupBox, QProgressBar, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QFrame,
    QGridLayout, QSizePolicy, QSpacerItem, QApplication, QListWidgetItem,
    QDateEdit, QToolBar, QAction, QStatusBar, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap, QPainter
from PyQt5 import QtWidgets, QtCore
from config.database import DB_CONFIG
from config.settings import CONFIG, save_config
from models.email import Email
from workers.email_fetch_worker import EmailFetchWorker, RealTimeEmailMonitor
from views.dialogs.email_account_dialog import EmailAccountDialog
from views.dialogs.custom_tag_rule_dialog import CustomTagRuleDialog
from views.dialogs.edit_rule_dialog import EditRuleDialog
from views.dialogs.advanced_search_dialog import AdvancedSearchDialog
from views.dialogs.bulk_operations_dialog import BulkOperationsDialog
from views.dialogs.attachment_cleanup_dialog import AttachmentCleanupDialog
from views.dialogs.settings_dialog import SettingsDialog
from views.dialogs.sync_dialog import SyncDialog
from views.dialogs.attachment_viewer_dialog import AttachmentViewerDialog
from views.dialogs.tag_attachments_dialog import TagAttachmentsDialog


from utils.formatters import format_size
from utils.email_formatter import EmailBodyFormatter
from config.settings import CONFIG


class EmailManagementWindow(QMainWindow):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.current_account_id = None
        self.real_time_monitor = None
        self.email_formatter = EmailBodyFormatter()
        
        # Defer heavy operations to make window open immediately
        self.accounts_loaded = False
        self.auto_sync_completed = False
        
        self.apply_modern_theme()
        self.init_ui()
        
        # Use QTimer to defer heavy operations after window is shown
        QTimer.singleShot(100, self.deferred_initialization)
        
        # Start real-time monitoring only if enabled and after window is ready
        if CONFIG.get('real_time_monitoring', True):
            QTimer.singleShot(500, self.start_real_time_monitoring)

    def deferred_initialization(self):
        """Deferred initialization to make window open immediately"""
        try:
            # Initialize worker attributes
            self.sync_worker = None
            self.auto_sync_worker = None
            self.worker_lock = False
            
            # Show initialization progress
            self.update_status_bar("Initializing application...")
            
            # First, load user accounts
            self.load_user_accounts()
            self.accounts_loaded = True
            
            # Then check if we have accounts and perform auto-sync
            if self.current_account_id:
                self.update_status_bar("Starting auto-sync...")
                QTimer.singleShot(1000, self.auto_sync_on_startup)
            else:
                # No accounts, mark as completed
                self.auto_sync_completed = True
                self.update_status_bar("Ready - No email accounts configured")
                
        except Exception as e:
            print(f"Deferred initialization error: {e}")
            self.update_status_bar("Initialization error occurred")
            self.accounts_loaded = True
            self.auto_sync_completed = True

    def apply_modern_theme(self):
        """Apply modern dark theme styling"""
        self.setStyleSheet("""
QMainWindow {
    background-color: #ffffff;
    color: #2d3748;
}

QWidget {
    background-color: #ffffff;
    color: #2d3748;
}

QGroupBox {
    font-weight: bold;
    font-size: 16px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    margin: 24px 0;
    padding-top: 18px;
    background-color: #ffffff;
    color: #2d3748;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: -2px;
    padding: 0 10px 0 10px;
    color: #4299e1;
    background: transparent;
    font-size: 15px;
    font-weight: bold;
}

/* Default Blue Buttons - All other buttons remain standard blue */
QPushButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #4299e1, stop: 1 #3182ce);
    border: 1px solid #4299e1;
    color: #ffffff;
    padding: 7px 20px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 16px;
    min-height: 25px;
}

QPushButton:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #2c5282, stop: 1 #2a4365);
    border-color: #2c5282;
    color: #ffffff;
}
                           
QMessageBox QPushButton {
    background-color: #0078D7;
    color: white;
    border-radius: 6px;
    padding: 5px 15px;
    font-weight: bold;
}
QMessageBox QPushButton:hover {
    background-color: #005A9E;
}


QPushButton:pressed {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #2c5282, stop: 1 #2a4365);
    border-color: #2c5282;
    color: #ffffff;
}

/* Light Blue Action Buttons - More blue that becomes dark blue on hover */
QPushButton[text="Add Account"],
QPushButton[text="ADD ACCOUNT"],
QPushButton[text="add account"],
QPushButton[text="Sync Now"],
QPushButton[text="SYNC NOW"],
QPushButton[text="sync now"],
QPushButton[text="Add Tag"],
QPushButton[text="ADD TAG"],
QPushButton[text="add tag"],
QPushButton[text="Custom Rule"],
QPushButton[text="CUSTOM RULE"],
QPushButton[text="custom rule"],
QPushButton[text="Get Attachments"],
QPushButton[text="GET ATTACHMENTS"],
QPushButton[text="get attachment"],
QPushButton[text="Clear All"],
QPushButton[text="CLEAR ALL"],
QPushButton[text="clear all"],
QPushButton[text="Edit Rule"],
QPushButton[text="EDIT RULE"],
QPushButton[text="edit rule"],
QPushButton[text="Toggle"],
QPushButton[text="TOGGLE"],
QPushButton[text="toggle"] {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #63b3ed, stop: 1 #4299e1);
    border: 1px solid #63b3ed;
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
}

/* View Attachments button - special handling for enabled/disabled states */
QPushButton[text="View Attachments"],
QPushButton[text="VIEW ATTACHMENTS"],
QPushButton[text="view attachment"] {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #63b3ed, stop: 1 #4299e1);
    border: 1px solid #63b3ed;
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
}

QPushButton[text="View Attachments"]:disabled,
QPushButton[text="VIEW ATTACHMENTS"]:disabled,
QPushButton[text="view attachment"]:disabled {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #a0aec0, stop: 1 #718096);
    border: 1px solid #a0aec0;
    color: #cbd5e0;
    font-size: 16px;
    font-weight: bold;
}

QPushButton[text="Add Account"]:hover,
QPushButton[text="ADD ACCOUNT"]:hover,
QPushButton[text="add account"]:hover,
QPushButton[text="Sync Now"]:hover,
QPushButton[text="SYNC NOW"]:hover,
QPushButton[text="sync now"]:hover,
QPushButton[text="Add Tag"]:hover,
QPushButton[text="ADD TAG"]:hover,
QPushButton[text="add tag"]:hover,
QPushButton[text="Custom Rule"]:hover,
QPushButton[text="CUSTOM RULE"]:hover,
QPushButton[text="custom rule"]:hover,
QPushButton[text="Get Attachments"]:hover,
QPushButton[text="GET ATTACHMENTS"]:hover,
QPushButton[text="get attachments"]:hover,
QPushButton[text="Clear All"]:hover,
QPushButton[text="CLEAR ALL"]:hover,
QPushButton[text="clear all"]:hover,
QPushButton[text="Edit Rule"]:hover,
QPushButton[text="EDIT RULE"]:hover,
QPushButton[text="edit rule"]:hover,
QPushButton[text="Toggle"]:hover,
QPushButton[text="TOGGLE"]:hover,
QPushButton[text="toggle"]:hover,
QPushButton[text="View Attachments"]:hover,
QPushButton[text="VIEW ATTACHMENTS"]:hover,
QPushButton[text="view attachments"]:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #2c5282, stop: 1 #2a4365);
    border-color: #2c5282;
    color: #ffffff;
}

QPushButton[text="Add Account"]:pressed,
QPushButton[text="ADD ACCOUNT"]:pressed,
QPushButton[text="add account"]:pressed,
QPushButton[text="Sync Now"]:pressed,
QPushButton[text="SYNC NOW"]:pressed,
QPushButton[text="sync now"]:pressed,
QPushButton[text="Add Tag"]:pressed,
QPushButton[text="ADD TAG"]:pressed,
QPushButton[text="add tag"]:pressed,
QPushButton[text="Custom Rule"]:pressed,
QPushButton[text="CUSTOM RULE"]:pressed,
QPushButton[text="custom rule"]:pressed,
QPushButton[text="Get Attachment"]:pressed,
QPushButton[text="GET ATTACHMENT"]:pressed,
QPushButton[text="get attachment"]:pressed,
QPushButton[text="Clear All"]:pressed,
QPushButton[text="CLEAR ALL"]:pressed,
QPushButton[text="clear all"]:pressed,
QPushButton[text="Edit Rule"]:pressed,
QPushButton[text="EDIT RULE"]:pressed,
QPushButton[text="edit rule"]:pressed,
QPushButton[text="Toggle"]:pressed,
QPushButton[text="TOGGLE"]:pressed,
QPushButton[text="toggle"]:pressed,
QPushButton[text="View Attachment"]:pressed,
QPushButton[text="VIEW ATTACHMENT"]:pressed,
QPushButton[text="view attachment"]:pressed {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #2c5282, stop: 1 #2a4365);
    border-color: #2c5282;
    color: #ffffff;
}

/* Cancel/Remove/Delete Buttons - Red that becomes darker red on hover */
QPushButton[text="Cancel"], 
QPushButton[text="CANCEL"],
QPushButton[text="cancel"],
QPushButton[text="Remove"],
QPushButton[text="REMOVE"], 
QPushButton[text="remove"],
QPushButton[text="Delete"],
QPushButton[text="DELETE"],
QPushButton[text="delete"] {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #f56565, stop: 1 #e53e3e);
    border: 1px solid #f56565;
    color: #ffffff;
    font-size: 16px;
}

QPushButton[text="Cancel"]:hover,
QPushButton[text="CANCEL"]:hover,
QPushButton[text="cancel"]:hover,
QPushButton[text="Remove"]:hover,
QPushButton[text="REMOVE"]:hover,
QPushButton[text="remove"]:hover,
QPushButton[text="Delete"]:hover,
QPushButton[text="DELETE"]:hover,
QPushButton[text="delete"]:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #e53e3e, stop: 1 #c53030);
    border-color: #e53e3e;
    color: #ffffff;
}

QPushButton[text="Cancel"]:pressed,
QPushButton[text="CANCEL"]:pressed,
QPushButton[text="cancel"]:pressed,
QPushButton[text="Remove"]:pressed,
QPushButton[text="REMOVE"]:pressed,
QPushButton[text="remove"]:pressed,
QPushButton[text="Delete"]:pressed,
QPushButton[text="DELETE"]:pressed,
QPushButton[text="delete"]:pressed {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #c53030, stop: 1 #9c2727);
    border-color: #c53030;
    color: #ffffff;
}

/* Alternative: Danger class for manual assignment */
QPushButton[class="danger"] {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #f56565, stop: 1 #e53e3e);
    border: 1px solid #f56565;
    color: #ffffff;
    font-size: 16px;
}

QPushButton[class="danger"]:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #e53e3e, stop: 1 #c53030);
    border-color: #e53e3e;
    color: #ffffff;
}

QPushButton[class="danger"]:pressed {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #c53030, stop: 1 #9c2727);
    border-color: #c53030;
    color: #ffffff;
}

QLineEdit, QComboBox, QDateEdit {
    padding: 10px 12px;
    border: 2px solid #e2e8f0;
    border-radius: 6px;
    background-color: #ffffff;
    color: #2d3748;
    font-size: 12px;
    selection-background-color: #4299e1;
    selection-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
    border-color: #4299e1;
    background-color: #ffffff;
    color: #2d3748;
}

QComboBox::drop-down {
    border: none;
    background: #f7fafc;
    width: 20px;
    border-radius: 0 6px 6px 0;
}

QComboBox::down-arrow {
    image: url(styles/icons/down-arrow.png);
    width: 17px;   /* adjust size */
    height: 17px;  /* adjust size */
    margin: 0 2px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 2px solid #e2e8f0;
    color: #2d3748;
    selection-background-color: #4299e1;
    selection-color: #ffffff;
}

QListWidget, QTreeWidget, QTextBrowser {
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    background-color: #ffffff;
    alternate-background-color: #f7fafc;
    selection-background-color: #4299e1;
    selection-color: #ffffff;
    outline: none;
    color: #2d3748;
    font-size: 12px;
}

QListWidget::item {
    padding: 10px;
    border-bottom: 1px solid #e2e8f0;
    border-radius: 4px;
    margin: 2px;
    color: #2d3748;
    font-size: 12px;
}

QListWidget::item:hover {
    background-color: #f7fafc;
    color: #2d3748;
}

QListWidget::item:selected {
    background-color: #4299e1;
    color: #ffffff;
}

QTreeWidget::item {
    padding: 8px;
    border-bottom: 1px solid #e2e8f0;
    color: #2d3748;
    font-size: 12px;
}

QTreeWidget::item:hover {
    background-color: #f7fafc;
    color: #2d3748;
}

QTreeWidget::item:selected {
    background-color: #4299e1;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #f7fafc;
    color: #2d3748;
    padding: 8px;
    border: 1px solid #e2e8f0;
    font-weight: bold;
    font-size: 12px;
}

QScrollBar:vertical {
    background-color: #ffffff;
    width: 12px;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e0;
    border-radius: 5px;
    min-height: 20px;
    margin: 1px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4299e1;
}

QScrollBar:horizontal {
    background-color: #ffffff;
    height: 12px;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
}

QScrollBar::handle:horizontal {
    background-color: #cbd5e0;
    border-radius: 5px;
    min-width: 20px;
    margin: 1px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4299e1;
}

QScrollBar::add-line, QScrollBar::sub-line {
    background: none;
    border: none;
}

QProgressBar {
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    text-align: center;
    background-color: #ffffff;
    color: #2d3748;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #4299e1, stop: 1 #3182ce);
    border-radius: 6px;
}

QMenuBar {
    background-color: #f7fafc;
    color: #2d3748;
    border-bottom: 1px solid #e2e8f0;
    padding: 4px;
    font-size: 12px;
}

QMenuBar::item {
    padding: 8px 12px;
    border-radius: 4px;
    color: #2d3748;
}

QMenuBar::item:selected {
    background-color: #4299e1;
    color: #ffffff;
}

QMenu {
    background-color: #ffffff;
    color: #2d3748;
    border: 2px solid #e2e8f0;
    border-radius: 6px;
    padding: 4px;
    font-size: 12px;
}

QMenu::item {
    padding: 8px 20px;
    border-radius: 4px;
    color: #2d3748;
}

QMenu::item:selected {
    background-color: #4299e1;
    color: #ffffff;
}

QStatusBar {
    background-color: #f7fafc;
    color: #2d3748;
    border-top: 1px solid #e2e8f0;
    padding: 4px;
    font-size: 12px;
}

QLabel {
    color: #2d3748;
    font-size: 12px;
}

QFrame {
    border: none;
    color: #2d3748;
    background-color: #ffffff;
}

QSplitter::handle {
    background-color: #e2e8f0;
    width: 3px;
    height: 3px;
}

QSplitter::handle:hover {
    background-color: #4299e1;
}

QTabWidget::pane {
    border: 2px solid #e2e8f0;
    border-radius: 6px;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: #f7fafc;
    color: #2d3748;
    padding: 8px 16px;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-size: 12px;
}

QTabBar::tab:selected {
    background-color: #4299e1;
    color: #ffffff;
}

QTabBar::tab:hover {
    background-color: #edf2f7;
    color: #2d3748;
}

QToolBar {
    background-color: #f7fafc;
    border: 1px solid #e2e8f0;
    padding: 4px;
    color: #2d3748;
    font-size: 12px;
}

QToolButton {
    background-color: transparent;
    color: #2d3748;
    padding: 8px;
    border-radius: 4px;
    border: none;
    font-size: 12px;
}

QToolButton:hover {
    background-color: #edf2f7;
    color: #2d3748;
}

QToolButton:pressed {
    background-color: #4299e1;
    color: #ffffff;
}

/* Specific styling for dialog text visibility */
QDialog {
    background-color: #ffffff;
    color: #2d3748;
}

QDialog QLabel {
    color: #2d3748;
    font-size: 12px;
}

QDialog QPushButton {
    color: #ffffff;
    font-size: 16px;
}

/* Ensure placeholder text is visible */
QLineEdit {
    color: #2d3748;
}

QLineEdit:placeholder {
    color: #a0aec0;
}

/* Calendar widget styling */
QCalendarWidget {
    background-color: #ffffff;
    color: #2d3748;
    font-size: 12px;
}

QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    color: #2d3748;
    selection-background-color: #4299e1;
    selection-color: #ffffff;
}

/* Date edit dropdown */
QDateEdit::drop-down {
    background-color: #f7fafc;
    border: none;
}

QDateEdit::down-arrow {
    image: url(styles/icons/down-arrow.png);
    width: 17px;   /* adjust size */
    height: 17px;  /* adjust size */
    margin: 0 2px;
}

/* Text areas and email content */
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #2d3748;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    selection-background-color: #4299e1;
    selection-color: #ffffff;
    font-size: 14px;
    line-height: 1.5;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #4299e1;
    outline: none;
}

/* Force all widgets to have white backgrounds */
QWidget {
    background-color: #ffffff !important;
    color: #2d3748 !important;
}

QFrame {
    background-color: #ffffff !important;
    color: #2d3748 !important;
}

QScrollArea {
    background-color: #ffffff !important;
    color: #2d3748 !important;
}

QScrollArea > QWidget {
    background-color: #ffffff !important;
    color: #2d3748 !important;
}

QScrollArea > QWidget > QWidget {
    background-color: #ffffff !important;
    color: #2d3748 !important;
}
        """)
    def init_ui(self):
        self.setWindowTitle("Email Management Dashboard")
        
        # Get screen size for responsive design
        screen = QApplication.desktop().screenGeometry()
        self.resize(min(1600, screen.width() - 100), min(1000, screen.height() - 100))
        
        # Center window
        self.move(screen.center() - self.rect().center())
        
        # Set up modern toolbar instead of menu bar
        self.create_modern_toolbar()
        
        # Create status bar with modern styling
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create main layout with modern splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout = QHBoxLayout(main_widget)
        main_layout.addWidget(main_splitter)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left panel - Account and Email List
        left_panel = self.create_modern_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Center panel - Email Content
        center_panel = self.create_modern_center_panel()
        main_splitter.addWidget(center_panel)
        
        # Right panel - Tags and Rules
        right_panel = self.create_modern_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setStretchFactor(2, 1)
        main_splitter.setSizes([400, 800, 400])

    def create_modern_toolbar(self):
        """Create modern toolbar with icons and grouped actions"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # File actions group
        add_account_action = QAction("Add Account", self)
        add_account_action.triggered.connect(self.add_email_account)
        toolbar.addAction(add_account_action)
        
        export_action = QAction("Export", self)
        export_action.triggered.connect(self.export_emails)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # Email actions group
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_emails)
        toolbar.addAction(refresh_action)
        
        mark_read_action = QAction("Mark Read", self)
        mark_read_action.triggered.connect(self.mark_selected_read)
        toolbar.addAction(mark_read_action)
        
        mark_unread_action = QAction("Mark Unread", self)
        mark_unread_action.triggered.connect(self.mark_selected_unread)
        toolbar.addAction(mark_unread_action)
        
        toolbar.addSeparator()
        
        # Tools group
        search_action = QAction("Advanced Search", self)
        search_action.triggered.connect(self.advanced_search)
        toolbar.addAction(search_action)
        
        attachments_action = QAction("Search Attachments", self)
        attachments_action.triggered.connect(self.search_attachments)
        toolbar.addAction(attachments_action)
        
        bulk_action = QAction("Bulk Operations", self)
        bulk_action.triggered.connect(self.bulk_operations)
        toolbar.addAction(bulk_action)
        
        toolbar.addSeparator()
        
        # Statistics action
        statistics_action = QAction("Statistics", self)
        statistics_action.triggered.connect(self.show_comprehensive_statistics)
        toolbar.addAction(statistics_action)
        
        toolbar.addSeparator()
        
        # Settings and logout
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)
        
        toolbar.addSeparator()
        
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout)
        toolbar.addAction(logout_action)

    def create_modern_left_panel(self):
        """Create modern left panel with enhanced styling"""
        left_widget = QFrame()
        left_widget.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_widget)
        
        # Account selection group - MOVED TO RIGHT PANEL
        account_group = QGroupBox("Email Accounts")
        account_layout = QVBoxLayout(account_group)
        
        # Account combo with modern styling
        self.account_combo = QComboBox()
        self.account_combo.currentIndexChanged.connect(self.account_changed)
        self.account_combo.setMinimumHeight(35)
        self.account_combo.setMinimumWidth(350)  # Increased width to prevent email cropping
        
        # Enhanced styling for account combo
        self.account_combo.setStyleSheet("""
            QComboBox {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
                font-weight: 500;
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px 12px;
                color: #2d3748;
            }
            QComboBox:hover {
                border-color: #cbd5e0;
            }
            QComboBox:focus {
                border-color: #3182ce;
                border-width: 3px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(styles/icons/down-arrow.png);
                width: 17px;   /* adjust size */
                height: 17px;  /* adjust size */
                margin: 0 2px;
            }
        """)
        
        account_layout.addWidget(self.account_combo)
        
        # Account management buttons in a modern grid
        account_btn_widget = QWidget()
        account_btn_layout = QGridLayout(account_btn_widget)
        account_btn_layout.setSpacing(8)
        
        add_account_btn = QPushButton("Add Account")
        add_account_btn.clicked.connect(self.add_email_account)
        add_account_btn.setProperty("class", "success")
        
        remove_account_btn = QPushButton("Remove")
        remove_account_btn.clicked.connect(self.remove_email_account)
        remove_account_btn.setProperty("class", "danger")
        
        sync_btn = QPushButton("Sync Now")
        sync_btn.clicked.connect(self.sync_emails)
        
        account_btn_layout.addWidget(add_account_btn, 0, 0)
        account_btn_layout.addWidget(remove_account_btn, 0, 1)
        account_btn_layout.addWidget(sync_btn, 1, 0, 1, 2)
        
        account_layout.addWidget(account_btn_widget)
        # Store account_group for use in right panel
        self.account_group = account_group
        
        # Email list group
        email_group = QGroupBox("Email List")
        email_layout = QVBoxLayout(email_group)
        
        # Modern search and filter section
        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        
        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search emails...")
        self.search_edit.textChanged.connect(self.filter_emails)
        self.search_edit.setMinimumHeight(35)
        
        # Enhanced styling for search box
        self.search_edit.setStyleSheet("""
            QLineEdit {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px 12px;
                color: #2d3748;
            }
            QLineEdit:focus {
                border-color: #3182ce;
                border-width: 3px;
            }
            QLineEdit::placeholder {
                color: #a0aec0;
                font-style: italic;
            }
        """)
        
        search_layout.addWidget(self.search_edit)
        
        # Filter controls
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Unread", "Read", "With Attachments", "Date Range"])
        self.filter_combo.currentTextChanged.connect(self.filter_emails)
        self.filter_combo.setMinimumHeight(30)
        
        # Enhanced styling for filter combo
        self.filter_combo.setStyleSheet("""
            QComboBox {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
                font-weight: 500;
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 10px;
                color: #2d3748;
            }
            QComboBox:hover {
                border-color: #cbd5e0;
            }
            QComboBox:focus {
                border-color: #3182ce;
                border-width: 3px;
            }
        """)
        
        filter_layout.addWidget(self.filter_combo)
        
        search_layout.addWidget(filter_widget)
        
        # Date range controls (initially hidden)
        date_widget = QWidget()
        date_layout = QGridLayout(date_widget)
        
        self.date_range_label = QLabel("Date Range:")
        self.date_range_label.setVisible(False)
        
        self.start_date_picker = QDateEdit()
        self.start_date_picker.setCalendarPopup(True)
        self.start_date_picker.setDate(QtCore.QDate.currentDate())
        self.start_date_picker.dateChanged.connect(self.filter_emails)
        self.start_date_picker.setVisible(False)
        self.start_date_picker.setMinimumHeight(30)
        
        # Enhanced styling for date pickers
        date_picker_style = """
            QDateEdit {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 10px;
                color: #2d3748;
            }
            QDateEdit:focus {
                border-color: #3182ce;
                border-width: 3px;
            }
        """
        self.start_date_picker.setStyleSheet(date_picker_style)
        
        self.end_date_picker = QDateEdit()
        self.end_date_picker.setCalendarPopup(True)
        self.end_date_picker.setDate(QtCore.QDate.currentDate())
        self.end_date_picker.dateChanged.connect(self.filter_emails)
        self.end_date_picker.setVisible(False)
        self.end_date_picker.setMinimumHeight(30)
        self.end_date_picker.setStyleSheet(date_picker_style)
        
        date_layout.addWidget(self.date_range_label, 0, 0, 1, 2)
        
        # Create From and To labels as instance variables for conditional visibility
        self.from_label = QLabel("From:")
        self.to_label = QLabel("To:")
        
        # Initially hide the From and To labels
        self.from_label.setVisible(False)
        self.to_label.setVisible(False)
        
        date_layout.addWidget(self.from_label, 1, 0)
        date_layout.addWidget(self.start_date_picker, 1, 1)
        date_layout.addWidget(self.to_label, 2, 0)
        date_layout.addWidget(self.end_date_picker, 2, 1)
        
        search_layout.addWidget(date_widget)
        email_layout.addWidget(search_widget)
        
        # Modern email list
        self.email_list = QListWidget()
        self.email_list.itemSelectionChanged.connect(self.email_selected)
        self.email_list.setAlternatingRowColors(False)  # Disabled alternating colors
        self.email_list.setSpacing(4)  # Increased spacing between items
        
        # Enhanced styling for better visibility
        self.email_list.setStyleSheet("""
            QListWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px;
                selection-background-color: #3182ce;
                selection-color: white;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px;
                border-radius: 6px;
                background-color: #f8fafc;  /* Light grey background for all items */
                border: 1px solid #e2e8f0;
            }
            QListWidget::item:hover {
                background-color: #edf2f7;
                border: 1px solid #cbd5e0;
            }
            QListWidget::item:selected {
                background-color: #3182ce;
                color: white;
                border: 1px solid #2b6cb0;
            }
        """)
        
        email_layout.addWidget(self.email_list)
        
        # Set consistent font for the entire email list
        font = self.email_list.font()
        font.setPointSize(11)
        font.setFamily("Segoe UI")
        self.email_list.setFont(font)
        
        # Email count with modern styling
        self.email_count_label = QLabel("0 emails")
        self.email_count_label.setAlignment(Qt.AlignCenter)
        self.email_count_label.setStyleSheet("""
            QLabel {
                color: #00d4ff;
                font-weight: bold;
                font-size: 11px;
                padding: 8px;
                background-color: #ffffff;
                border-radius: 4px;
                margin: 4px;
            }
        """)
        email_layout.addWidget(self.email_count_label)
        
        left_layout.addWidget(email_group)
        
        return left_widget

    def create_modern_center_panel(self):
        """Create modern center panel with enhanced email display"""
        center_widget = QFrame()
        center_layout = QVBoxLayout(center_widget)
        
        # Email content display
        content_group = QGroupBox("Email Content")
        content_layout = QVBoxLayout(content_group)
        content_layout.setSpacing(4)  # Minimal spacing between main sections
        content_layout.setContentsMargins(8, 6, 8, 8)  # Reduced top margin to move header up
        
        # Email headers with modern card design - ultra compact
        headers_card = QFrame()
        headers_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                padding: 6px;
                margin: 1px;
                font-size: 12px;
            }
        """)
        headers_layout = QFormLayout(headers_card)
        headers_layout.setSpacing(2)  # Minimal spacing between form rows
        headers_layout.setContentsMargins(6, 4, 6, 4)  # Minimal margins, especially top
        
        self.subject_label = QLabel()
        self.subject_label.setWordWrap(True)
        self.subject_label.setStyleSheet("font-weight: bold; font-size: 17px; color: #363636; margin: 1px; padding: 1px;")
        
        self.sender_label = QLabel()
        self.sender_label.setStyleSheet("color: #363636; font-size: 15px; margin: 1px; padding: 1px;")
        
        self.date_label = QLabel()
        self.date_label.setStyleSheet("color: #363636; font-size: 15px; margin: 1px; padding: 1px;")
        
        self.recipients_label = QLabel()
        self.recipients_label.setWordWrap(True)
        self.recipients_label.setStyleSheet("color: #363636; font-size: 15px; margin: 1px; padding: 1px;")
        
        headers_layout.addRow("Subject:", self.subject_label)
        headers_layout.addRow("From:", self.sender_label)
        headers_layout.addRow("Date:", self.date_label)
        headers_layout.addRow("To:", self.recipients_label)
        
        content_layout.addWidget(headers_card)
        
        # Make header section take minimal space
        content_layout.setStretchFactor(headers_card, 0)
        
        # Add minimal spacer to push header up and give more space to email body
        from PyQt5.QtWidgets import QSpacerItem, QSizePolicy
        header_spacer = QSpacerItem(20, 3, QSizePolicy.Minimum, QSizePolicy.Fixed)
        content_layout.addItem(header_spacer)
        
        # Email body with enhanced display - more prominent
        self.email_content = QTextBrowser()
        self.email_content.setReadOnly(True)
        self.email_content.setOpenExternalLinks(True)
        self.email_content.setAcceptRichText(True)
        self.email_content.setMinimumHeight(350)  # Increased minimum height for better readability
        self.email_content.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 16px;
                font-size: 13px;
                line-height: 1.6;
                margin: 4px;
            }
        """)
        content_layout.addWidget(self.email_content)
        
        # Make email body expand to fill available space
        content_layout.setStretchFactor(self.email_content, 1)
        
        # Email actions with modern button styling - more compact
        actions_card = QFrame()
        actions_card.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 6px;
                margin: 2px;
            }
        """)
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setContentsMargins(6, 4, 6, 4)  # Reduce margins
        
        self.attachments_btn = QPushButton("View Attachments")
        self.attachments_btn.clicked.connect(self.view_attachments)
        self.attachments_btn.setEnabled(False)
        self.attachments_btn.setProperty("class", "info")
        self.attachments_btn.setToolTip("No attachments available for this email")
        
        self.content_type_label = QLabel("Auto-detecting content...")
        self.content_type_label.setStyleSheet("color: #ffffff; font-size: 10px; font-style: italic;")
        
        actions_layout.addWidget(self.attachments_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(self.content_type_label)
        
        content_layout.addWidget(actions_card)
        
        # Tag management with modern design - more compact
        tag_card = QFrame()
        tag_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                padding: 6px;
                margin: 2px;
            }
        """)
        tag_layout = QHBoxLayout(tag_card)
        tag_layout.setContentsMargins(6, 4, 6, 4)  # Reduce margins
        
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("Enter tag name...")
        self.tag_edit.returnPressed.connect(self.add_tag_to_email)
        self.tag_edit.setMinimumHeight(32)
        
        custom_tag_btn = QPushButton("Custom Rule")
        custom_tag_btn.clicked.connect(self.create_custom_tag_rule)
        custom_tag_btn.setProperty("class", "warning")
        
        add_tag_btn = QPushButton("Add Tag")
        add_tag_btn.clicked.connect(self.add_tag_to_email)
        add_tag_btn.setProperty("class", "success")
        
        tag_layout.addWidget(self.tag_edit, 2)
        tag_layout.addWidget(add_tag_btn, 1)
        tag_layout.addWidget(custom_tag_btn, 1)
        
        content_layout.addWidget(tag_card)
        center_layout.addWidget(content_group)
        
        return center_widget

    def create_modern_right_panel(self):
        """Create modern right panel with enhanced tag and rule management"""
        right_widget = QFrame()
        right_widget.setMaximumWidth(450)  # Increased from 400 to accommodate wider account combo
        right_layout = QVBoxLayout(right_widget)
        
        # Email Accounts panel - MOVED FROM LEFT PANEL
        if hasattr(self, 'account_group'):
            right_layout.addWidget(self.account_group)
            right_layout.addSpacing(8)  # Reduced spacing from 15 to 8
        
        # Tags panel with modern design
        tags_group = QGroupBox("Tags")
        tags_layout = QVBoxLayout(tags_group)
        
        self.tags_list = QListWidget()
        self.tags_list.itemDoubleClicked.connect(self.filter_by_tag)
        self.tags_list.setSpacing(3)
        
        # Enhanced styling for tags list
        self.tags_list.setStyleSheet("""
            QListWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 6px;
                margin: 1px;
                border-radius: 4px;
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
            }
            QListWidget::item:hover {
                background-color: #edf2f7;
                border: 1px solid #cbd5e0;
            }
            QListWidget::item:selected {
                background-color: #3182ce;
                color: white;
                border: 1px solid #2b6cb0;
            }
        """)
        
        tags_layout.addWidget(self.tags_list)
        
        # Tag management buttons in modern grid
        tag_btn_widget = QWidget()
        tag_btn_layout = QGridLayout(tag_btn_widget)
        tag_btn_layout.setSpacing(6)
        
        attachments_btn = QPushButton("Get Attachments")
        attachments_btn.clicked.connect(self.fetch_tag_attachments)
        attachments_btn.setProperty("class", "success")
        
        delete_tag_btn = QPushButton("Delete Tag")
        delete_tag_btn.clicked.connect(self.delete_tag)
        delete_tag_btn.setProperty("class", "danger")
        
        clear_all_tags_btn = QPushButton("Clear All")
        clear_all_tags_btn.clicked.connect(self.clear_all_tags_from_emails)
        clear_all_tags_btn.setProperty("class", "warning")
        
        tag_btn_layout.addWidget(attachments_btn, 0, 0)
        tag_btn_layout.addWidget(delete_tag_btn, 0, 1)
        tag_btn_layout.addWidget(clear_all_tags_btn, 1, 0, 1, 2)
        
        tags_layout.addWidget(tag_btn_widget)
        right_layout.addWidget(tags_group)
        right_layout.addSpacing(10)  # Add spacing between Tags and Auto-Tag Rules
        
        # Auto-tag rules panel - Made taller with larger inner box
        rules_group = QGroupBox("Auto-Tag Rules")
        rules_layout = QVBoxLayout(rules_group)
        rules_layout.setSpacing(8)  # Increased spacing between elements
        
        self.rules_tree = QTreeWidget()
        self.rules_tree.setHeaderLabels(["Type", "Value", "Tag", "Attachments", "Status"])
        self.rules_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.rules_tree.setAlternatingRowColors(True)
        self.rules_tree.setMinimumHeight(200)  # Set minimum height for larger inner box
        
        # Enhanced styling for rules tree
        self.rules_tree.setStyleSheet("""
            QTreeWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px;
            }
            QTreeWidget::item {
                padding: 4px;
                margin: 1px;
                border-radius: 3px;
            }
            QTreeWidget::item:hover {
                background-color: #edf2f7;
            }
            QTreeWidget::item:selected {
                background-color: #3182ce;
                color: white;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 8px;
                border: 1px solid #e2e8f0;
                font-weight: 600;
                color: #2d3748;
            }
        """)
        
        rules_layout.addWidget(self.rules_tree)
        
        # Rules management buttons
        rules_btn_widget = QWidget()
        rules_btn_layout = QGridLayout(rules_btn_widget)
        rules_btn_layout.setSpacing(6)
        
        edit_rule_btn = QPushButton("Edit Rule")
        edit_rule_btn.clicked.connect(self.edit_rule)
        
        toggle_rule_btn = QPushButton("Toggle")
        toggle_rule_btn.clicked.connect(self.toggle_rule)
        toggle_rule_btn.setProperty("class", "warning")
        
        delete_rule_btn = QPushButton("Delete")
        delete_rule_btn.clicked.connect(self.delete_rule)
        delete_rule_btn.setProperty("class", "danger")
        
        rules_btn_layout.addWidget(edit_rule_btn, 0, 0)
        rules_btn_layout.addWidget(toggle_rule_btn, 0, 1)
        rules_btn_layout.addWidget(delete_rule_btn, 1, 0, 1, 2)
        
        rules_layout.addWidget(rules_btn_widget)
        right_layout.addWidget(rules_group)
        
        return right_widget

    def load_user_accounts(self):
        """Load email accounts for the current user with loading indicator"""
        self.account_combo.clear()
        
        # Show loading indicator
        self.update_status_bar("Loading accounts...")
        
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, email, imap_host, last_sync, sync_enabled, session_expires
                FROM accounts 
                WHERE dashboard_user_id=%s AND (session_expires IS NULL OR session_expires > NOW())
                ORDER BY created_at DESC
            """, (self.user_id,))
            
            accounts = cursor.fetchall()
            
            for account_id, email, imap_host, last_sync, sync_enabled, session_expires in accounts:
                status = "🟢" if sync_enabled else "🔴"
                sync_info = f"Last: {last_sync.strftime('%m/%d %H:%M')}" if last_sync else "Never"
                display_text = f"{status} {email} @ {imap_host} ({sync_info})"
                
                self.account_combo.addItem(display_text, account_id)
                
            if accounts:
                self.account_combo.setCurrentIndex(0)
                self.current_account_id = self.account_combo.currentData()
                self.update_status_bar(f"Loaded {len(accounts)} account(s)")
                # Defer account change operations to avoid blocking UI
                QTimer.singleShot(50, self.account_changed)
            else:
                self.update_status_bar("No email accounts found")
                
        except Exception as e:
            print(f"Error loading accounts: {e}")
            self.update_status_bar("Error loading accounts")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def account_changed(self):
        """Handle account selection change with deferred operations"""
        if self.account_combo.currentData():
            self.current_account_id = self.account_combo.currentData()
            self.filter_combo.setCurrentText("All")
            self.date_range_label.setVisible(False)
            self.start_date_picker.setVisible(False)
            self.end_date_picker.setVisible(False)
            
            # Defer heavy operations to avoid blocking UI
            QTimer.singleShot(50, self.deferred_account_operations)
        else:
            self.current_account_id = None

    def deferred_account_operations(self):
        """Deferred account operations to keep UI responsive"""
        try:
            # Update UI elements that don't require heavy operations
            self.filter_combo.setCurrentText("All")
            
            # Defer each heavy operation with small delays to keep UI responsive
            QTimer.singleShot(100, self.refresh_emails)
            QTimer.singleShot(200, self.load_tags)
            QTimer.singleShot(300, self.load_rules)
            QTimer.singleShot(400, self.update_statistics)
            QTimer.singleShot(500, self.start_real_time_monitoring)
            
            # Mark account operations as completed
            self.accounts_loaded = True
            
        except Exception as e:
            print(f"Deferred account operations error: {e}")
            self.update_status_bar("Error loading account data")
            self.accounts_loaded = True

    def add_email_account(self):
        """Add new email account dialog"""
        dialog = EmailAccountDialog(self, self.user_id)
        if dialog.exec_() == dialog.Accepted:
            self.load_user_accounts()

    def remove_email_account(self):
        """Remove selected email account"""
        if not self.current_account_id:
            QMessageBox.warning(self, "No Account", "Please select an account to remove.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Removal",
            "Are you sure you want to remove this email account?\n\n"
            "This will delete all associated emails, tags, and rules.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM accounts WHERE id=%s", (self.current_account_id,))
                conn.commit()
                
                QMessageBox.information(self, "Account Removed", "Email account removed successfully.")
                self.load_user_accounts()
            finally:
                cursor.close()
                conn.close()

    def sync_emails(self):
        """Sync emails for current account with modern progress dialog"""
        if not self.current_account_id:
            QMessageBox.warning(self, "No Account", "Please select an account first.")
            return
            
        # Check if any worker is already running
        if self.is_worker_running():
            QMessageBox.information(self, "Operation in Progress", 
                "Email sync is already running. Please wait for it to complete.")
            return
            
        sync_dialog = SyncDialog(self)
        if sync_dialog.exec_() != sync_dialog.Accepted:
            return
            
        sync_info = sync_dialog.get_sync_info()
        if not sync_info:
            QMessageBox.warning(self, "Sync Error", "Invalid sync option selected.")
            return
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT imap_host, imap_port, email, encrypted_password 
                FROM accounts 
                WHERE id=%s
            """, (self.current_account_id,))
            
            account_info = cursor.fetchone()
            if not account_info:
                QMessageBox.warning(self, "Account Error", "Account not found.")
                return
                
            self.sync_worker = EmailFetchWorker(account_info, self.user_id, sync_info['start_date'])
            self.sync_worker.progress.connect(self.update_sync_progress)
            self.sync_worker.finished.connect(self.sync_completed)
            self.sync_worker.error.connect(self.sync_error)
            self.sync_worker.emails_processed.connect(self.update_sync_progress_count)
            self.sync_worker.batch_complete.connect(self.add_emails_to_ui)
            
            # Create modern progress dialog
            self.create_modern_progress_dialog(sync_info)
            
            self.sync_timeout_timer = QTimer()
            self.sync_timeout_timer.setSingleShot(True)
            self.sync_timeout_timer.timeout.connect(self.sync_timeout)
            self.sync_timeout_timer.start(900000)
            
            self.total_emails_to_process = 0
            self.current_emails_processed = 0
            self.new_emails_fetched = 0
            
            self.progress_animation_timer = QTimer()
            self.progress_animation_timer.timeout.connect(self.animate_initial_progress)
            self.progress_animation_timer.start(100)
            
            # Set worker lock to prevent conflicts
            self.set_worker_lock(True)
            
            self.progress_dialog.show()
            self.progress_dialog.raise_()
            self.progress_dialog.activateWindow()
            self.sync_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Sync Error", f"Failed to start sync: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def create_modern_progress_dialog(self, sync_info):
        """Create a modern-styled progress dialog"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
        
        self.progress_dialog = QDialog(self)
        self.progress_dialog.setWindowTitle(f"Syncing Emails - {sync_info['description']}")
        self.progress_dialog.setModal(True)
        self.progress_dialog.resize(600, 250)
        
        # Apply modern styling to progress dialog
        self.progress_dialog.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #2d3748;
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
                padding: 4px;
            }
            QProgressBar {
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                text-align: center;
                background-color: #ffffff;
                color: #2d3748;
                font-weight: bold;
                height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00d4ff, stop: 1 #0099cc);
                border-radius: 6px;
            }
        """)
        
        main_rect = self.geometry()
        dialog_x = main_rect.x() + (main_rect.width() - 600) // 2
        dialog_y = main_rect.y() + (main_rect.height() - 250) // 2
        self.progress_dialog.move(dialog_x, dialog_y)
        
        self.progress_dialog.setWindowFlags(
            self.progress_dialog.windowFlags() | 
            Qt.WindowStaysOnTopHint
        )
        
        layout = QVBoxLayout(self.progress_dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Modern title
        title_label = QLabel("Syncing Emails")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #00d4ff;
                text-align: center;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Modern progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Initializing... %p%")
        layout.addWidget(self.progress_bar)
        
        # Status label with modern styling
        self.progress_status_label = QLabel("Connecting to email server...")
        self.progress_status_label.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                color: #363636;
            }
        """)
        layout.addWidget(self.progress_status_label)
        
        # Modern cancel button
        cancel_button = QPushButton("Cancel Sync")
        cancel_button.clicked.connect(self.cancel_sync)
        cancel_button.setProperty("class", "danger")
        cancel_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f44336, stop: 1 #c62828);
                border: none;
                color:#ffffff;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ef5350, stop: 1 #d32f2f);
            }
        """)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def update_sync_progress_count(self, current_count, total_count):
        """Update sync progress with email count information"""
        QTimer.singleShot(0, lambda: self._update_progress_internal(current_count, total_count))
    
    def _update_progress_internal(self, current_count, total_count):
        """Internal method to update progress (called on main thread)"""
        self.current_emails_processed = current_count
        self.total_emails_to_process = total_count
        
        if total_count > 0:
            percentage = int((current_count / total_count) * 100)
            
            if hasattr(self, 'progress_bar') and self.progress_bar and not self.progress_bar.isHidden():
                try:
                    self.update_progress_bar(percentage, f"Processing emails... {current_count:,}/{total_count:,} ({percentage}%)")
                except RuntimeError:
                    pass
            
            if hasattr(self, 'progress_status_label') and self.progress_status_label:
                try:
                    progress_text = f"Processing email {self.current_emails_processed:,} of {self.total_emails_to_process:,} ({percentage}%)\n"
                    progress_text += f"New emails found: {self.new_emails_fetched:,}"
                    self.progress_status_label.setText(progress_text)
                    
                except RuntimeError:
                    pass
        
        self.update_status_bar(f"Processing email {current_count:,} of {total_count:,}")

    def add_emails_to_ui(self, emails_batch):
        """Add a batch of newly fetched emails to the UI in real-time"""
        try:
            QTimer.singleShot(0, lambda: self._process_emails_batch(emails_batch))
        except Exception as e:
            print(f"Error scheduling emails batch: {e}")
    
    def _process_emails_batch(self, emails_batch):
        """Process emails batch in a non-blocking way"""
        try:
            self.new_emails_fetched += len(emails_batch)
            
            for email_data in emails_batch:
                item = QListWidgetItem()
                
                status_icon = "📧" if not email_data.get('read_status', False) else "📖"
                attachment_icon = "📎" if email_data.get('has_attachment', False) else ""
                date_str = email_data['date'].strftime("%m/%d %H:%M") if email_data['date'] else ""
                
                display_subject = (email_data['subject'][:50] + "...") if len(email_data['subject']) > 50 else email_data['subject']
                display_sender = (email_data['sender'][:30] + "...") if len(email_data['sender']) > 30 else email_data['sender']
                
                item_text = f"{status_icon} {attachment_icon} [{date_str}] {display_subject}\n    From: {display_sender}"
                item.setText(item_text)
                
                item.setData(Qt.UserRole, email_data['id'])
                
                self.email_list.insertItem(0, item)
            
            self.update_email_count()
            
            if hasattr(self, 'progress_dialog') and self.progress_dialog and self.progress_dialog.isVisible():
                try:
                    progress_text = f"Processing email {self.current_emails_processed:,} of {self.total_emails_to_process:,}\n"
                    progress_text += f"New emails found: {self.new_emails_fetched:,}"
                    self.update_progress_dialog(progress_text)
                except RuntimeError:
                    pass
                
        except Exception as e:
            print(f"Error processing emails batch: {e}")

    def update_email_count(self):
        """Update the email count label"""
        QTimer.singleShot(0, self._update_email_count_internal)
    
    def _update_email_count_internal(self):
        """Internal method to update email count (called on main thread)"""
        try:
            total_count = self.email_list.count()
            self.email_count_label.setText(f"{total_count:,} emails")
        except Exception as e:
            print(f"Error updating email count: {e}")
    
    def update_status_bar(self, message):
        """Update status bar in a non-blocking way"""
        QTimer.singleShot(0, lambda: self.statusBar().showMessage(message))
    
    def update_progress_dialog(self, progress_text):
        """Update progress dialog in a non-blocking way"""
        QTimer.singleShot(0, lambda: self._update_progress_dialog_internal(progress_text))
    
    def _update_progress_dialog_internal(self, progress_text):
        """Internal method to update progress dialog (called on main thread)"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog and self.progress_dialog.isVisible():
            try:
                if hasattr(self, 'progress_status_label') and self.progress_status_label:
                    self.progress_status_label.setText(progress_text)
            except RuntimeError:
                pass
    
    def update_progress_bar(self, percentage, format_text):
        """Update progress bar in a non-blocking way"""
        QTimer.singleShot(0, lambda: self._update_progress_bar_internal(percentage, format_text))
    
    def _update_progress_bar_internal(self, percentage, format_text):
        """Internal method to update progress bar (called on main thread)"""
        if hasattr(self, 'progress_bar') and self.progress_bar and not self.progress_bar.isHidden():
            try:
                self.progress_bar.setValue(percentage)
                self.progress_bar.setFormat(format_text)
            except RuntimeError:
                pass

    def cancel_sync(self):
        """Cancel the email sync operation"""
        if hasattr(self, 'sync_worker') and self.sync_worker.isRunning():
            self.sync_worker.stop()
            self.sync_worker.wait(3000)
            
            if self.sync_worker.isRunning():
                self.sync_worker.terminate()
                self.sync_worker.wait(1000)
        
        if hasattr(self, 'progress_dialog'):
            try:
                self.progress_dialog.close()
            except:
                pass  # Ignore errors when closing dialog
            self.progress_dialog = None
            
        if hasattr(self, 'sync_timeout_timer'):
            self.sync_timeout_timer.stop()
            
        if hasattr(self, 'progress_animation_timer'):
            self.progress_animation_timer.stop()
            
        self.update_status_bar("Sync cancelled by user")

    def sync_timeout(self):
        """Handle sync timeout for large email volumes"""
        QMessageBox.warning(self, "Sync Timeout", 
                           "Email sync is taking longer than expected and will be cancelled.\n\n"
                           f"Current Progress:\n"
                           f"• Emails processed: {self.current_emails_processed:,}\n"
                           f"• Total emails found: {self.total_emails_to_process:,}\n"
                           f"• New emails found: {self.new_emails_fetched:,}\n\n"
                           "This might be due to:\n"
                           "• Very large number of emails in the selected time period\n"
                           "• Slow internet connection or server response\n"
                           "• Complex email content processing\n\n"
                           "Tips for large email volumes:\n"
                           "• Try syncing a smaller time period first\n"
                           "• Check your internet connection\n"
                           "• The progressive loading ensures emails are saved as they're processed\n"
                           "• You can resume syncing from where you left off")
        
        if hasattr(self, 'progress_animation_timer'):
            self.progress_animation_timer.stop()
            
        self.cancel_sync()

    def update_sync_progress(self, message):
        """Update sync progress"""
        QTimer.singleShot(0, lambda: self._update_progress_message_internal(message))
    
    def _update_progress_message_internal(self, message):
        """Internal method to update progress message (called on main thread)"""
        if hasattr(self, 'progress_status_label') and self.progress_status_label:
            try:
                if "Found" in message and "emails to process" in message:
                    try:
                        total_count = int(message.split("Found ")[1].split(" ")[0])
                        self.total_emails_to_process = total_count
                        self.current_emails_processed = 0
                        
                        if hasattr(self, 'progress_bar') and self.progress_bar:
                            self.update_progress_bar(0, f"Processing emails... 0/{total_count:,} (0%)")
                        
                        progress_text = f"Found {total_count:,} emails to process\n"
                        progress_text += f"Starting progressive loading...\n"
                        progress_text += f"New emails found: 0"
                        self.progress_status_label.setText(progress_text)
                    except (ValueError, IndexError):
                        self.progress_status_label.setText(message)
                else:
                    self.progress_status_label.setText(message)
            except RuntimeError:
                pass
        
        self.update_status_bar(message)

    def sync_completed(self, new_count):
        """Handle sync completion with progressive loading results"""
        if hasattr(self, 'progress_dialog'):
            try:
                self.progress_dialog.close()
            except:
                pass  # Ignore errors when closing dialog
            self.progress_dialog = None
            
        if hasattr(self, 'sync_timeout_timer'):
            self.sync_timeout_timer.stop()
            
        if hasattr(self, 'progress_animation_timer'):
            self.progress_animation_timer.stop()
        
        self.update_status_bar(f"Sync completed! Processed {self.total_emails_to_process:,} emails, found {new_count:,} new emails")
        
        if new_count > 0:
            QMessageBox.information(self, "Sync Complete", 
                                  f"Successfully completed progressive email sync!\n\n"
                                  f"Results:\n"
                                  f"• Total emails processed: {self.total_emails_to_process:,}\n"
                                  f"• New emails found: {new_count:,}\n"
                                  f"• Emails already existed: {self.total_emails_to_process - new_count:,}\n\n"
                                  f"All emails within the selected time period have been fetched using progressive loading.")
        else:
            QMessageBox.information(self, "Sync Complete", 
                                  f"Sync completed successfully!\n\n"
                                  f"Results:\n"
                                  f"• Total emails processed: {self.total_emails_to_process:,}\n"
                                  f"• New emails found: {new_count:,}\n"
                                  f"• All emails were already in the database\n\n"
                                  f"Progressive loading ensured the application remained responsive throughout the process.")
        
        self.refresh_emails()
        self.update_statistics()
        self.load_tags()
        self.load_rules()
        
        self.total_emails_to_process = 0
        self.current_emails_processed = 0
        self.new_emails_fetched = 0
        
        # Release worker lock
        self.set_worker_lock(False)

    def sync_error(self, error_message):
        """Handle sync error"""
        if hasattr(self, 'progress_dialog'):
            try:
                self.progress_dialog.close()
            except:
                pass  # Ignore errors when closing dialog
            self.progress_dialog = None
            
        if hasattr(self, 'sync_timeout_timer'):
            self.sync_timeout_timer.stop()
            
        if hasattr(self, 'progress_animation_timer'):
            self.progress_animation_timer.stop()
        
        self.update_status_bar("Sync failed")
        
        error_text = f"Failed to sync emails:\n\n{error_message}\n\n"
        
        if "timeout" in error_message.lower():
            error_text += "This appears to be a timeout issue. Try:\n"
            error_text += "• Checking your internet connection\n"
            error_text += "• Reducing the time range for sync\n"
            error_text += "• Trying again later"
        elif "login" in error_message.lower() or "auth" in error_message.lower():
            error_text += "This appears to be an authentication issue. Try:\n"
            error_text += "• Checking your email password\n"
            error_text += "• Verifying IMAP settings\n"
            error_text += "• Checking if 2FA is required"
        elif "database" in error_message.lower():
            error_text += "This appears to be a database issue. Try:\n"
            error_text += "• Checking database connection\n"
            error_text += "• Contacting support if problem persists"
        else:
            error_text += "Try:\n"
            error_text += "• Checking your internet connection\n"
            error_text += "• Verifying your email settings\n"
            error_text += "• Trying again in a few minutes"
        
        QMessageBox.critical(self, "Sync Error", error_text)
        
        # Release worker lock
        self.set_worker_lock(False)

    def auto_sync_on_startup(self):
        """Automatically sync emails when application starts - non-blocking"""
        if not self.current_account_id:
            return
            
        # Check if any worker is already running
        if self.is_worker_running():
            print("⚠ Auto-sync on startup skipped - another operation is in progress")
            return
            
        # Show status message
        self.update_status_bar("Preparing auto-sync...")
        
        # Defer auto-sync to avoid blocking startup
        QTimer.singleShot(2000, self.perform_auto_sync)
        
    def perform_auto_sync(self):
        """Perform automatic sync on startup"""
        if not self.current_account_id:
            return
            
        sync_dialog = SyncDialog(self)
        sync_dialog.today_radio.setChecked(True)
        
        QTimer.singleShot(100, lambda: self.auto_accept_sync_dialog(sync_dialog))
        
    def auto_accept_sync_dialog(self, sync_dialog):
        """Auto-accept the sync dialog for startup sync"""
        if sync_dialog.exec_() == sync_dialog.Accepted:
            sync_info = sync_dialog.get_sync_info()
            if sync_info:
                self.perform_sync_with_info(sync_info)
                
    def perform_sync_with_info(self, sync_info):
        """Perform sync with the given sync info using progressive loading"""
        if not self.current_account_id:
            return
            
        # Check if any worker is already running
        if self.is_worker_running():
            print("⚠ Auto-sync skipped - another operation is in progress")
            return
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT imap_host, imap_port, email, encrypted_password 
                FROM accounts 
                WHERE id=%s
            """, (self.current_account_id,))
            
            account_info = cursor.fetchone()
            if not account_info:
                return
                
            self.auto_sync_worker = EmailFetchWorker(account_info, self.user_id, sync_info['start_date'])
            self.auto_sync_worker.finished.connect(self.auto_sync_completed)
            self.auto_sync_worker.error.connect(self._handle_auto_sync_error)
            self.auto_sync_worker.emails_processed.connect(self.update_auto_sync_progress)
            self.auto_sync_worker.batch_complete.connect(self.add_emails_to_ui)
            
            # Set worker lock to prevent conflicts
            self.set_worker_lock(True)
            
            self.update_status_bar(f"Auto-sync emails - {sync_info['description']}")
            
            self.auto_sync_worker.start()
            
        except Exception as e:
            print(f"Auto-sync error: {e}")
        finally:
            cursor.close()
            conn.close()

    def update_auto_sync_progress(self, current_count, total_count):
        """Update auto-sync progress during startup"""
        QTimer.singleShot(0, lambda: self._update_auto_sync_progress_internal(current_count, total_count))
    
    def _update_auto_sync_progress_internal(self, current_count, total_count):
        """Internal method to update auto-sync progress (called on main thread)"""
        if total_count > 0:
            percentage = int((current_count / total_count) * 100)
            status_msg = f"Auto-sync: Processing email {current_count:,} of {total_count:,} ({percentage}%)"
            self.update_status_bar(status_msg)
            
            if current_count % 50 == 0:
                QApplication.processEvents()

    def auto_sync_completed(self, new_count):
        """Handle auto-sync completion"""
        if new_count > 0:
            self.update_status_bar(f"Auto-sync completed: Found {new_count:,} new emails")
            self.refresh_emails()
            self.update_statistics()
            self.load_tags()
            self.load_rules()
        else:
            self.update_status_bar("Auto-sync completed: No new emails found")
            
        if hasattr(self, 'total_emails_to_process'):
            self.total_emails_to_process = 0
        if hasattr(self, 'current_emails_processed'):
            self.current_emails_processed = 0
        if hasattr(self, 'new_emails_fetched'):
            self.new_emails_fetched = 0
            
        # Release worker lock
        self.set_worker_lock(False)
        
    def auto_sync_error(self, error_message):
        """Handle auto-sync error silently"""
        try:
            # Ensure error_message is a string and handle all possible types
            if error_message is None:
                error_message = "Unknown error occurred"
            elif isinstance(error_message, bool):
                error_message = "Unknown error occurred" if error_message else "No error details"
            elif isinstance(error_message, (int, float)):
                error_message = f"Error code: {error_message}"
            elif not isinstance(error_message, str):
                error_message = str(error_message)
                
            self.update_status_bar("Auto-sync failed")
            print(f"Auto-sync error: {error_message}")
        except Exception as e:
            print(f"Error handling auto-sync error: {e}")
            self.update_status_bar("Auto-sync error occurred")
            
        # Release worker lock
        self.set_worker_lock(False)
        
    def start_real_time_monitoring(self):
        """Start real-time email monitoring"""
        if not CONFIG.get('real_time_monitoring', True):
            return
            
        if not self.current_account_id:
            return
            
        self.stop_real_time_monitoring()
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT imap_host, imap_port, email, encrypted_password 
                FROM accounts 
                WHERE id=%s
            """, (self.current_account_id,))
            
            account_info = cursor.fetchone()
            if not account_info:
                return
                
            self.real_time_monitor = RealTimeEmailMonitor(account_info, self.user_id)
            self.real_time_monitor.new_emails.connect(self.on_new_emails_found)
            self.real_time_monitor.error.connect(self.on_monitoring_error)
            self.real_time_monitor.start()
            
            self.update_status_bar("Real-time monitoring started")
            
        except Exception as e:
            print(f"Error starting real-time monitoring: {e}")
        finally:
            cursor.close()
            conn.close()
            
    def stop_real_time_monitoring(self):
        """Stop real-time email monitoring"""
        if self.real_time_monitor and self.real_time_monitor.isRunning():
            self.real_time_monitor.stop()
            self.real_time_monitor.wait()
            self.real_time_monitor = None
            self.update_status_bar("Real-time monitoring stopped")
            
    def on_new_emails_found(self, count):
        """Handle new emails found by real-time monitoring"""
        if count > 0:
            self.update_status_bar(f"Real-time: Found {count} new emails")
            self.refresh_emails()
            self.update_statistics()
            self.load_tags()
            self.load_rules()
            
    def on_monitoring_error(self, error_message):
        """Handle real-time monitoring errors"""
        print(f"Real-time monitoring error: {error_message}")
        QTimer.singleShot(60000, self.start_real_time_monitoring)

    def refresh_emails(self):
        """Refresh email list with modern styling"""
        if not self.current_account_id:
            self.email_list.clear()
            self.email_count_label.setText("0 emails")
            return
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT e.id, e.subject, e.sender, e.date, e.read_status, e.has_attachment,
                       GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ', ') as tags
                FROM emails e
                LEFT JOIN email_tags et ON e.id = et.email_id
                LEFT JOIN tags t ON et.tag_id = t.id
                WHERE e.account_id = %s
            """
            params = [self.current_account_id]
            
            search_text = self.search_edit.text().strip()
            if search_text:
                query += """ AND (e.subject LIKE %s OR e.sender LIKE %s OR 
                                 e.body LIKE %s OR e.body_text LIKE %s OR e.body_html LIKE %s)"""
                search_pattern = f"%{search_text}%"
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])
            
            status_filter = self.filter_combo.currentText()
            if status_filter == "Unread":
                query += " AND e.read_status = FALSE"
            elif status_filter == "Read":
                query += " AND e.read_status = TRUE"
            elif status_filter == "With Attachments":
                query += " AND e.has_attachment = TRUE"
            elif status_filter == "Date Range":
                start_date = self.start_date_picker.date().toPyDate()
                end_date = self.end_date_picker.date().toPyDate()
                query += " AND DATE(e.date) BETWEEN %s AND %s"
                params.extend([start_date, end_date])
            
            query += " GROUP BY e.id ORDER BY e.date DESC"
            
            cursor.execute(query, params)
            emails = cursor.fetchall()
            
            self.email_list.clear()
            for email_id, subject, sender, date, read_status, has_attachment, tags in emails:
                status_icon = "📧" if not read_status else "📖"
                attachment_icon = "📎" if has_attachment else ""
                date_str = date.strftime("%m/%d %H:%M") if date else ""
                
                display_subject = (subject[:50] + "...") if len(subject) > 50 else subject
                display_sender = (sender[:30] + "...") if len(sender) > 30 else sender
                
                # Enhanced formatting for better readability
                item_text = f"{status_icon} {attachment_icon} [{date_str}] {display_subject}\n    From: {display_sender}"
                
                if tags:
                    item_text += f" 🏷️ {tags}"
                
                # Add some visual separation for better readability
                item_text = f"  {item_text}"  # Add left padding
                
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(Qt.UserRole, email_id)
                
                # Enhanced font styling for better visibility
                try:
                    font = item.font()
                    font.setPointSize(11)  # Larger, more visible font size
                    font.setFamily("Segoe UI")  # Modern, readable font
                    
                    if not read_status:
                        font.setBold(True)
                        font.setPointSize(12)  # Even larger for unread emails
                    
                    item.setFont(font)
                except Exception as e:
                    print(f"Font setting error: {e}")
                    # Fallback to default font if there's an issue
                
                # Set text color for better contrast
                if not read_status:
                    item.setForeground(QColor("#1a365d"))  # Dark blue for unread
                else:
                    item.setForeground(QColor("#2d3748"))  # Dark gray for read
                
                self.email_list.addItem(item)
            
            if status_filter == "Date Range":
                start_date = self.start_date_picker.date().toPyDate()
                end_date = self.end_date_picker.date().toPyDate()
                self.email_count_label.setText(f"{len(emails)} emails from {start_date} to {end_date}")
            else:
                self.email_count_label.setText(f"{len(emails)} emails")
            
        finally:
            cursor.close()
            conn.close()

    def email_selected(self):
        """Handle email selection with modern content display"""
        current_item = self.email_list.currentItem()
        if not current_item:
            return
            
        email_id = current_item.data(Qt.UserRole)
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT subject, sender, recipients, date, body, read_status, has_attachment
                FROM emails 
                WHERE id=%s
            """, (email_id,))
            
            result = cursor.fetchone()
            if not result:
                return
                
            subject, sender, recipients, date, body, read_status, has_attachment = result
            
            self.subject_label.setText(subject or "(No subject)")
            self.sender_label.setText(sender or "(Unknown sender)")
            self.recipients_label.setText(recipients or "(No recipients)")
            self.date_label.setText(date.strftime("%Y-%m-%d %H:%M:%S") if date else "(No date)")
            
            email = Email.get_by_id(email_id)
            if email:
                self.display_email_content(email)
            else:
                self.email_content.setPlainText(body or "No content available.")
            
            self._update_attachments_button_state(has_attachment)
            
            if not read_status:
                cursor.execute("UPDATE emails SET read_status=TRUE WHERE id=%s", (email_id,))
                conn.commit()
                self.refresh_emails()
                
        finally:
            cursor.close()
            conn.close()

    def view_attachments(self):
        """Open attachment viewer for the selected email"""
        current_item = self.email_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an email to view attachments.")
            return
            
        email_id = current_item.data(Qt.UserRole)
        
        dialog = AttachmentViewerDialog(self, email_id, self.user_id)
        dialog.exec_()
    
    def display_email_content(self, email):
        """Display email content with enhanced MIME parsing and inline image support"""
        if not email:
            self.email_content.setPlainText("No content available.")
            self.content_type_label.setText("📄 No content")
            return
        
        body_text = email.body_text or email.body
        body_html = email.body_html
        
        inline_images = getattr(email, 'inline_images', []) or []
        
        # For complex HTML content, use async processing to prevent UI freezing
        if body_html and body_html.strip() and len(body_html) > 10000:
            self._display_email_async(email, body_text, body_html, inline_images)
            return
        
        try:
            if body_html and body_html.strip():
                formatted_content, _ = self.email_formatter.format_email_body(
                    text_body=body_text,
                    html_body=body_html,
                    prefer_html=True,
                    inline_images=inline_images
                )
                self.email_content.setHtml(formatted_content)
                
                if email.body_format == 'both':
                    self.content_type_label.setText(" Rich HTML + Text")
                elif email.body_format == 'html':
                    self.content_type_label.setText(" Rich HTML Email")
                else:
                    self.content_type_label.setText("Auto-detected HTML")
                    
                if inline_images:
                    self.content_type_label.setText(f"Rich HTML + {len(inline_images)} Images")
                    
            elif body_text and body_text.strip():
                formatted_content, _ = self.email_formatter.format_email_body(
                    text_body=body_text,
                    html_body=None,
                    prefer_html=False
                )
                self.email_content.setHtml(formatted_content)
                
                if email.body_format == 'text':
                    self.content_type_label.setText("📝 Enhanced Text")
                else:
                    self.content_type_label.setText("📝 Auto-enhanced Text")
                    
            else:
                self.email_content.setPlainText("No content available.")
                self.content_type_label.setText("📄 No content")
                return
            
            content_info = []
            if body_html and body_html.strip():
                content_info.append("HTML")
            if body_text and body_text.strip():
                content_info.append("Text")
            if inline_images:
                content_info.append(f"{len(inline_images)} Images")
            
            if content_info:
                word_count = self.email_formatter.get_word_count(body_text or body_html or "")
                content_type = self.email_formatter.detect_content_type(body_html or body_text or "")
                info_text = f"Auto-display: {', '.join(content_info)} | Words: {word_count} | Type: {content_type}"
                self.update_status_bar(info_text)
            else:
                self.update_status_bar("Email displayed with automatic formatting")
                
        except Exception as e:
            print(f"Error displaying email content: {e}")
            fallback_content = body_text or body_html or "Error displaying content"
            if body_html and not body_text:
                try:
                    fallback_content = self.email_formatter.extract_plain_text(body_html)
                except:
                    fallback_content = "Error processing email content"
            
            self.email_content.setPlainText(fallback_content)
            self.content_type_label.setText("📄 Fallback Text")
            self.update_status_bar("Displayed in fallback mode due to formatting error")
    
    def _display_email_async(self, email, body_text, body_html, inline_images):
        """Display email content asynchronously to prevent UI freezing"""
        try:
            # Stop any existing HTML worker
            if hasattr(self, 'html_worker') and self.html_worker and self.html_worker.thread.isRunning():
                self.html_worker.stop()
                self.html_worker.thread.wait(1000)  # Wait up to 1 second
            
            # Show loading state with progress indicator
            loading_text = f"""Processing complex email content...

Content size: {len(body_html):,} characters
This may take a moment for emails with advanced formatting.

Processing in background to keep the application responsive..."""
            
            self.email_content.setPlainText(loading_text)
            self.content_type_label.setText("Processing...")
            self.update_status_bar("Processing complex HTML email in background...")
            
            # Create async worker for HTML processing
            def process_html():
                try:
                    # Add a small delay to show the loading state
                    import time
                    time.sleep(0.1)
                    
                    formatted_content, _ = self.email_formatter.format_email_body(
                        text_body=body_text,
                        html_body=body_html,
                        prefer_html=True,
                        inline_images=inline_images
                    )
                    return formatted_content, email.body_format, inline_images
                except Exception as e:
                    print(f"Error in async HTML processing: {e}")
                    return None, 'error', []
            
            # Create and start worker with proper cleanup
            from workers.async_worker import AsyncWorker
            self.html_worker = AsyncWorker(process_html)
            self.html_worker.finished.connect(lambda result: self._on_html_processed(result, email))
            self.html_worker.error.connect(lambda error: self._on_html_error(error, body_text, body_html))
            
            # Store email reference to prevent garbage collection issues
            self.html_worker.email_ref = email
            self.html_worker.start()
            
        except Exception as e:
            print(f"Error setting up async HTML processing: {e}")
            # Fallback to immediate processing
            self._process_html_immediately(email, body_text, body_html, inline_images)
    
    def _process_html_immediately(self, email, body_text, body_html, inline_images):
        """Process HTML content immediately as fallback when async fails"""
        try:
            formatted_content, _ = self.email_formatter.format_email_body(
                text_body=body_text,
                html_body=body_html,
                prefer_html=True,
                inline_images=inline_images
            )
            
            self.email_content.setHtml(formatted_content)
            
            # Update content type label
            if email.body_format == 'both':
                self.content_type_label.setText(" ")
            elif email.body_format == 'html':
                self.content_type_label.setText(" ")
            else:
                self.content_type_label.setText(" ")
                
            if inline_images:
                self.content_type_label.setText(f"Rich HTML + {len(inline_images)} Images")
            
            # Update status bar
            self._update_content_info(email, inline_images)
            self.update_status_bar("Email processed immediately (async failed)")
            
        except Exception as e:
            print(f"Error in immediate HTML processing: {e}")
            # Final fallback to text
            fallback_content = body_text or "Error processing email content"
            self.email_content.setPlainText(fallback_content)
            self.content_type_label.setText("📄 Fallback Text")
            self.update_status_bar("Displayed in fallback mode due to processing error")
    
    def _on_html_processed(self, result, email):
        """Handle completed HTML processing"""
        if result and len(result) >= 3:
            formatted_content, body_format, inline_images = result
            
            # Update UI on main thread
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._update_email_display(
                formatted_content, body_format, inline_images, email
            ))
        else:
            self._on_html_error("Invalid result from HTML processing", 
                               getattr(email, 'body_text', ''), 
                               getattr(email, 'body_html', ''))
    
    def _on_html_error(self, error, body_text, body_html):
        """Handle HTML processing errors"""
        print(f"HTML processing error: {error}")
        
        # Fallback to text display
        fallback_content = body_text or body_html or "Error processing email content"
        if body_html and not body_text:
            try:
                fallback_content = self.email_formatter.extract_plain_text(body_html)
            except:
                fallback_content = "Error processing email content"
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._update_email_display_fallback(fallback_content))
    
    def _update_email_display(self, formatted_content, body_format, inline_images, email):
        """Update email display with processed content (called on main thread)"""
        try:
            self.email_content.setHtml(formatted_content)
            
            # Update content type label
            if body_format == 'both':
                self.content_type_label.setText(" ")
            elif body_format == 'html':
                self.content_type_label.setText(" ")
            else:
                self.content_type_label.setText(" ")
                
            if inline_images:
                self.content_type_label.setText(f"Rich HTML + {len(inline_images)} Images")
            
            # Update status bar
            self._update_content_info(email, inline_images)
            
        except Exception as e:
            print(f"Error updating email display: {e}")
            self._update_email_display_fallback("Error updating email display")
    
    def _update_email_display_fallback(self, fallback_content):
        """Update email display with fallback content"""
        self.email_content.setPlainText(fallback_content)
        self.content_type_label.setText("📄 Fallback Text")
        self.update_status_bar("Displayed in fallback mode due to formatting error")
    
    def _update_content_info(self, email, inline_images):
        """Update content information display"""
        body_text = getattr(email, 'body_text', None) or ""
        body_html = getattr(email, 'body_html', None) or ""
        
        content_info = []
        if body_html and body_html.strip():
            content_info.append("HTML")
        if body_text and body_text.strip():
            content_info.append("Text")
        if inline_images:
            content_info.append(f"{len(inline_images)} Images")
        
        if content_info:
            word_count = self.email_formatter.get_word_count(body_text or body_html or "")
            content_type = self.email_formatter.detect_content_type(body_html or body_text or "")
            info_text = f"Auto-display: {', '.join(content_info)} | Words: {word_count} | Type: {content_type}"
            self.update_status_bar(info_text)
        else:
            self.update_status_bar("Email displayed with automatic formatting")

    def filter_emails(self):
        """Filter emails based on search and status"""
        current_filter = self.filter_combo.currentText()
        if current_filter == "Date Range":
            self.date_range_label.setVisible(True)
            self.from_label.setVisible(True)
            self.start_date_picker.setVisible(True)
            self.to_label.setVisible(True)
            self.end_date_picker.setVisible(True)
        else:
            self.date_range_label.setVisible(False)
            self.from_label.setVisible(False)
            self.start_date_picker.setVisible(False)
            self.to_label.setVisible(False)
            self.end_date_picker.setVisible(False)
        
        self.refresh_emails()

    def clear_all_tags_from_emails(self):
        """Remove all tags from all emails (useful for testing)"""
        if not self.current_account_id:
            QMessageBox.warning(self, "No Account", "Please select an account first.")
            return
            
        reply = QMessageBox.question(
            self, "Clear All Tags",
            "This will remove ALL tags from ALL emails for the current account.\n\n"
            "This action is mainly for testing purposes.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE et FROM email_tags et
                INNER JOIN emails e ON et.email_id = e.id
                WHERE e.account_id = %s
            """, (self.current_account_id,))
            
            removed_count = cursor.rowcount
            conn.commit()
            
            self.refresh_emails()
            self.update_statistics()
            self.load_tags()
            
            QMessageBox.information(
                self, "Tags Cleared",
                f"Removed {removed_count} tag associations from emails."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear tags: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def add_tag_to_email(self):
        """Add tag to selected email with immediate feedback"""
        current_item = self.email_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an email to tag.")
            return
            
        tag_name = self.tag_edit.text().strip()
        if not tag_name:
            QMessageBox.warning(self, "No Tag", "Please enter a tag name.")
            return
            
        email_id = current_item.data(Qt.UserRole)
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM tags WHERE name=%s AND dashboard_user_id=%s", 
                         (tag_name, self.user_id))
            result = cursor.fetchone()
            
            if result:
                tag_id = result[0]
            else:
                cursor.execute("INSERT INTO tags (name, dashboard_user_id) VALUES (%s, %s)", 
                             (tag_name, self.user_id))
                conn.commit()
                tag_id = cursor.lastrowid
            
            cursor.execute("INSERT IGNORE INTO email_tags (email_id, tag_id) VALUES (%s, %s)", 
                         (email_id, tag_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                self.update_status_bar(f"Tagged email with '{tag_name}'")
                self.tag_edit.clear()
                
                self.refresh_emails()
                self.load_tags()
                
                QTimer.singleShot(2000, lambda: self.update_status_bar("Ready"))
            else:
                self.update_status_bar("Email already has this tag")
                QTimer.singleShot(2000, lambda: self.update_status_bar("Ready"))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add tag: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    def create_custom_tag_rule(self):
        """Create custom tag rule dialog (renamed from auto-tag sender)"""
        current_item = self.email_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an email to create a rule from.")
            return
            
        email_id = current_item.data(Qt.UserRole)
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT sender FROM emails WHERE id=%s", (email_id,))
            result = cursor.fetchone()
            if not result:
                return
                
            sender = result[0]
            
            dialog = CustomTagRuleDialog(self, sender, self.user_id)
            if dialog.exec_() == dialog.Accepted:
                self.load_rules()
                self.load_tags()
                self.refresh_emails()
                self.update_statistics()
                
                self.update_status_bar("Custom tag rule created and applied!")
                QTimer.singleShot(3000, lambda: self.update_status_bar("Ready"))
                
        finally:
            cursor.close()
            conn.close()

    def load_tags(self):
        """Load tags for current user with modern styling"""
        self.tags_list.clear()
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT t.name, COUNT(et.email_id) as usage_count
                FROM tags t
                LEFT JOIN email_tags et ON t.id = et.tag_id
                LEFT JOIN emails e ON et.email_id = e.id
                WHERE t.dashboard_user_id = %s AND (e.account_id = %s OR e.account_id IS NULL)
                GROUP BY t.id, t.name
                ORDER BY usage_count DESC, t.name
            """, (self.user_id, self.current_account_id or 0))
            
            for tag_name, usage_count in cursor.fetchall():
                item_text = f"{tag_name} ({usage_count})"
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(Qt.UserRole, tag_name)
                self.tags_list.addItem(item)
                
        finally:
            cursor.close()
            conn.close()

    def load_rules(self):
        """Load auto-tag rules with modern tree styling"""
        self.rules_tree.clear()
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT r.id, r.rule_type, r.operator, r.value, t.name, r.enabled, 
                       r.save_attachments, r.attachment_path
                FROM auto_tag_rules r
                JOIN tags t ON r.tag_id = t.id
                WHERE r.dashboard_user_id = %s
                ORDER BY r.priority DESC, r.rule_type
            """, (self.user_id,))
            
            for rule_id, rule_type, operator, value, tag_name, enabled, save_attachments, attachment_path in cursor.fetchall():
                status = "✅" if enabled else "❌"
                attachment_status = "💾" if save_attachments else "❌"
                display_value = (value[:30] + "...") if len(value) > 30 else value
                
                item = QTreeWidgetItem([
                    rule_type,
                    f"{operator}: {display_value}",
                    tag_name,
                    attachment_status,
                    status
                ])
                item.setData(0, Qt.UserRole, rule_id)
                self.rules_tree.addTopLevelItem(item)
                
        finally:
            cursor.close()
            conn.close()

    def show_comprehensive_statistics(self):
        """Show comprehensive statistics dialog with all functions"""
        if not self.current_account_id:
            QMessageBox.warning(self, "No Account", "Please select an email account to view statistics.")
            return
            
        # Create statistics dialog
        stats_dialog = QDialog(self)
        stats_dialog.setWindowTitle("Email Statistics")
        stats_dialog.setModal(True)
        stats_dialog.resize(600, 450)  # Reduced from 800x600 to 600x450
        
        # Apply modern styling
        stats_dialog.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #2d3748;
            }
            QGroupBox {
                font-weight: 600;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                color: #2d3748;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 8px 0 8px;
                background-color: #f8fafc;
                color: #2d3748;
                font-size: 10pt;
            }
            QLabel {
                color: #2d3748;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #3182ce;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2a4365;
            }
            QPushButton:pressed {
                background-color: #1e3250;
            }
        """)
        
        layout = QVBoxLayout(stats_dialog)
        layout.setSpacing(8)  # Reduced spacing between groups
        layout.setContentsMargins(15, 15, 15, 15)  # Reduced margins
        
        # Get comprehensive statistics
        stats_data = self.get_comprehensive_statistics()
        
        # Email Overview Section
        overview_group = QGroupBox("Email Overview")
        overview_layout = QGridLayout(overview_group)
        overview_layout.setSpacing(4)  # Reduced spacing between grid items
        overview_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins
        
        overview_layout.addWidget(QLabel("Total Emails:"), 0, 0)
        overview_layout.addWidget(QLabel(f"{stats_data['total_emails']:,}"), 0, 1)
        
        overview_layout.addWidget(QLabel("Unread Emails:"), 1, 0)
        overview_layout.addWidget(QLabel(f"{stats_data['unread_emails']:,}"), 1, 1)
        
        overview_layout.addWidget(QLabel("Read Emails:"), 2, 0)
        overview_layout.addWidget(QLabel(f"{stats_data['read_emails']:,}"), 2, 1)
        
        overview_layout.addWidget(QLabel("Emails with Attachments:"), 3, 0)
        overview_layout.addWidget(QLabel(f"{stats_data['with_attachments']:,}"), 3, 1)
        
        overview_layout.addWidget(QLabel("Total Storage Used:"), 4, 0)
        overview_layout.addWidget(QLabel(f"{stats_data['total_size_formatted']}"), 4, 1)
        
        layout.addWidget(overview_group)
        
        # Time-based Statistics
        time_group = QGroupBox("Time-based Statistics")
        time_layout = QGridLayout(time_group)
        time_layout.setSpacing(4)  # Reduced spacing between grid items
        time_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins
        
        time_layout.addWidget(QLabel("This Week:"), 0, 0)
        time_layout.addWidget(QLabel(f"{stats_data['this_week']:,} emails"), 0, 1)
        
        time_layout.addWidget(QLabel("This Month:"), 1, 0)
        time_layout.addWidget(QLabel(f"{stats_data['this_month']:,} emails"), 1, 1)
        
        time_layout.addWidget(QLabel("This Year:"), 2, 0)
        time_layout.addWidget(QLabel(f"{stats_data['this_year']:,} emails"), 2, 1)
        
        time_layout.addWidget(QLabel("Oldest Email:"), 3, 0)
        time_layout.addWidget(QLabel(f"{stats_data['oldest_email']}"), 3, 1)
        
        time_layout.addWidget(QLabel("Newest Email:"), 4, 0)
        time_layout.addWidget(QLabel(f"{stats_data['newest_email']}"), 4, 1)
        
        layout.addWidget(time_group)
        
        # Tag Statistics
        tag_group = QGroupBox("Tag Statistics")
        tag_layout = QGridLayout(tag_group)
        tag_layout.setSpacing(4)  # Reduced spacing between grid items
        tag_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins
        
        tag_layout.addWidget(QLabel("Total Tags:"), 0, 0)
        tag_layout.addWidget(QLabel(f"{stats_data['total_tags']:,}"), 0, 1)
        
        tag_layout.addWidget(QLabel("Most Used Tag:"), 1, 0)
        tag_layout.addWidget(QLabel(f"{stats_data['most_used_tag']} ({stats_data['most_used_count']:,} times)"), 1, 1)
        
        tag_layout.addWidget(QLabel("Untagged Emails:"), 2, 0)
        tag_layout.addWidget(QLabel(f"{stats_data['untagged_emails']:,}"), 2, 1)
        
        layout.addWidget(tag_group)
        
        # Sender Statistics
        sender_group = QGroupBox("Sender Statistics")
        sender_layout = QGridLayout(sender_group)
        sender_layout.setSpacing(4)  # Reduced spacing between grid items
        sender_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins
        
        sender_layout.addWidget(QLabel("Top Sender:"), 0, 0)
        sender_layout.addWidget(QLabel(f"{stats_data['top_sender']} ({stats_data['top_sender_count']:,} emails)"), 0, 1)
        
        sender_layout.addWidget(QLabel("Unique Senders:"), 1, 0)
        sender_layout.addWidget(QLabel(f"{stats_data['unique_senders']:,}"), 1, 1)
        
        sender_layout.addWidget(QLabel("Average Emails per Sender:"), 2, 0)
        sender_layout.addWidget(QLabel(f"{stats_data['avg_emails_per_sender']:.1f}"), 2, 1)
        
        layout.addWidget(sender_group)
        
        # Auto-tag Rules Statistics
        rules_group = QGroupBox("Auto-tag Rules Statistics")
        rules_layout = QGridLayout(rules_group)
        rules_layout.setSpacing(4)  # Reduced spacing between grid items
        rules_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins
        
        rules_layout.addWidget(QLabel("Total Rules:"), 0, 0)
        rules_layout.addWidget(QLabel(f"{stats_data['total_rules']:,}"), 0, 1)
        
        rules_layout.addWidget(QLabel("Active Rules:"), 1, 0)
        rules_layout.addWidget(QLabel(f"{stats_data['active_rules']:,}"), 1, 1)
        
        rules_layout.addWidget(QLabel("Rules with Attachments:"), 2, 0)
        rules_layout.addWidget(QLabel(f"{stats_data['rules_with_attachments']:,}"), 2, 1)
        
        layout.addWidget(rules_group)
        
        # Performance Statistics
        perf_group = QGroupBox("Performance Statistics")
        perf_layout = QGridLayout(perf_group)
        
        perf_group.setVisible(False)  # Hide for now, can be expanded later
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(stats_dialog.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #e53e3e;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #c53030;
            }
        """)
        
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
        
        # Show dialog
        stats_dialog.exec_()

    def get_comprehensive_statistics(self):
        """Get comprehensive statistics for the current account"""
        if not self.current_account_id:
            return {}
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Basic email statistics
            cursor.execute("SELECT COUNT(*) FROM emails WHERE account_id=%s", (self.current_account_id,))
            total_emails = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM emails WHERE account_id=%s AND read_status=FALSE", 
                         (self.current_account_id,))
            unread_emails = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM emails WHERE account_id=%s AND read_status=TRUE", 
                         (self.current_account_id,))
            read_emails = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM emails WHERE account_id=%s AND has_attachment=TRUE", 
                         (self.current_account_id,))
            with_attachments = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(size_bytes) FROM emails WHERE account_id=%s", 
                         (self.current_account_id,))
            total_size = cursor.fetchone()[0] or 0
            
            # Time-based statistics
            cursor.execute("""
                SELECT COUNT(*) FROM emails 
                WHERE account_id=%s AND date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """, (self.current_account_id,))
            this_week = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM emails 
                WHERE account_id=%s AND date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """, (self.current_account_id,))
            this_month = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM emails 
                WHERE account_id=%s AND date >= DATE_SUB(NOW(), INTERVAL 365 DAY)
            """, (self.current_account_id,))
            this_year = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT MIN(date), MAX(date) FROM emails WHERE account_id=%s
            """, (self.current_account_id,))
            date_range = cursor.fetchone()
            oldest_email = date_range[0].strftime("%Y-%m-%d") if date_range[0] else "N/A"
            newest_email = date_range[1].strftime("%Y-%m-%d") if date_range[1] else "N/A"
            
            # Tag statistics
            cursor.execute("""
                SELECT COUNT(DISTINCT t.id) FROM tags t
                JOIN email_tags et ON t.id = et.tag_id
                JOIN emails e ON et.email_id = e.id
                WHERE e.account_id = %s
            """, (self.current_account_id,))
            total_tags = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT t.name, COUNT(et.email_id) as usage_count
                FROM tags t
                JOIN email_tags et ON t.id = et.tag_id
                JOIN emails e ON et.email_id = e.id
                WHERE e.account_id = %s
                GROUP BY t.id, t.name
                ORDER BY usage_count DESC
                LIMIT 1
            """, (self.current_account_id,))
            most_used_result = cursor.fetchone()
            most_used_tag = most_used_result[0] if most_used_result else "N/A"
            most_used_count = most_used_result[1] if most_used_result else 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM emails e
                LEFT JOIN email_tags et ON e.id = et.email_id
                WHERE e.account_id = %s AND et.email_id IS NULL
            """, (self.current_account_id,))
            untagged_emails = cursor.fetchone()[0]
            
            # Sender statistics
            cursor.execute("""
                SELECT sender, COUNT(*) as email_count
                FROM emails
                WHERE account_id = %s
                GROUP BY sender
                ORDER BY email_count DESC
                LIMIT 1
            """, (self.current_account_id,))
            top_sender_result = cursor.fetchone()
            top_sender = top_sender_result[0] if top_sender_result else "N/A"
            top_sender_count = top_sender_result[1] if top_sender_result else 0
            
            cursor.execute("""
                SELECT COUNT(DISTINCT sender) FROM emails WHERE account_id = %s
            """, (self.current_account_id,))
            unique_senders = cursor.fetchone()[0]
            
            avg_emails_per_sender = total_emails / unique_senders if unique_senders > 0 else 0
            
            # Auto-tag rules statistics
            cursor.execute("""
                SELECT COUNT(*) FROM auto_tag_rules WHERE dashboard_user_id = %s
            """, (self.user_id,))
            total_rules = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM auto_tag_rules WHERE dashboard_user_id = %s AND enabled = TRUE
            """, (self.user_id,))
            active_rules = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM auto_tag_rules WHERE dashboard_user_id = %s AND save_attachments = TRUE
            """, (self.user_id,))
            rules_with_attachments = cursor.fetchone()[0]
            
            return {
                'total_emails': total_emails,
                'unread_emails': unread_emails,
                'read_emails': read_emails,
                'with_attachments': with_attachments,
                'total_size': total_size,
                'total_size_formatted': format_size(total_size),
                'this_week': this_week,
                'this_month': this_month,
                'this_year': this_year,
                'oldest_email': oldest_email,
                'newest_email': newest_email,
                'total_tags': total_tags,
                'most_used_tag': most_used_tag,
                'most_used_count': most_used_count,
                'untagged_emails': untagged_emails,
                'top_sender': top_sender,
                'top_sender_count': top_sender_count,
                'unique_senders': unique_senders,
                'avg_emails_per_sender': avg_emails_per_sender,
                'total_rules': total_rules,
                'active_rules': active_rules,
                'rules_with_attachments': rules_with_attachments
            }
            
        finally:
            cursor.close()
            conn.close()

    def update_statistics(self):
        """Update statistics display - now handled by comprehensive statistics dialog"""
        # This method is kept for compatibility but no longer updates a stats label
        # Statistics are now displayed through the comprehensive statistics dialog
        pass

    def filter_by_tag(self, item):
        """Filter emails by selected tag - show emails directly"""
        tag_name = item.data(Qt.UserRole)
        if not tag_name or not self.current_account_id:
            return
            
        self.search_edit.clear()
        self.filter_combo.setCurrentText("All")
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM tags WHERE name=%s AND dashboard_user_id=%s", 
                         (tag_name, self.user_id))
            tag_result = cursor.fetchone()
            
            if not tag_result:
                self.email_list.clear()
                self.email_count_label.setText("0 emails")
                return
                
            tag_id = tag_result[0]
            
            query = """
                SELECT e.id, e.subject, e.sender, e.date, e.read_status, e.has_attachment,
                       GROUP_CONCAT(DISTINCT t2.name ORDER BY t2.name SEPARATOR ', ') as all_tags
                FROM emails e
                INNER JOIN email_tags et ON e.id = et.email_id
                LEFT JOIN email_tags et2 ON e.id = et2.email_id
                LEFT JOIN tags t2 ON et2.tag_id = t2.id
                WHERE e.account_id = %s AND et.tag_id = %s
                GROUP BY e.id
                ORDER BY e.date DESC
            """
            
            cursor.execute(query, (self.current_account_id, tag_id))
            emails = cursor.fetchall()
            
            self.email_list.clear()
            for email_id, subject, sender, date, read_status, has_attachment, tags in emails:
                status_icon = "📧" if not read_status else "📖"
                attachment_icon = "📎" if has_attachment else ""
                date_str = date.strftime("%m/%d %H:%M") if date else ""
                
                display_subject = (subject[:50] + "...") if len(subject) > 50 else subject
                display_sender = (sender[:30] + "...") if len(sender) > 30 else sender
                
                item_text = f"{status_icon} {attachment_icon} [{date_str}] {display_subject}\n    From: {display_sender}"
                if tags:
                    item_text += f" 🏷️ {tags}"
                
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(Qt.UserRole, email_id)
                
                if not read_status:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                
                self.email_list.addItem(item)
            
            self.email_count_label.setText(f"{len(emails)} emails with tag '{tag_name}'")
            self.update_status_bar(f"Showing emails tagged with '{tag_name}'")
            
        finally:
            cursor.close()
            conn.close()

    def delete_tag(self):
        """Delete selected tag"""
        current_item = self.tags_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a tag to delete.")
            return
            
        tag_name = current_item.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete tag '{tag_name}'?\n\nThis will remove it from all emails.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM tags WHERE name=%s AND dashboard_user_id=%s", 
                             (tag_name, self.user_id))
                conn.commit()
                
                self.load_tags()
                self.load_rules()
                self.refresh_emails()
                self.update_status_bar(f"Tag '{tag_name}' deleted")
            finally:
                cursor.close()
                conn.close()

    def fetch_tag_attachments(self):
        """Open dialog to fetch attachments for selected tag"""
        current_item = self.tags_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a tag to fetch attachments for.")
            return
            
        dialog = TagAttachmentsDialog(self, self.user_id)
        if dialog.exec_() == dialog.Accepted:
            self.update_status_bar("Attachments fetched successfully")

    def edit_rule(self):
        """Edit selected auto-tag rule"""
        current_item = self.rules_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a rule to edit.")
            return
            
        rule_id = current_item.data(0, Qt.UserRole)
        
        dialog = EditRuleDialog(self, rule_id, self.user_id)
        if dialog.exec_() == dialog.Accepted:
            self.load_rules()

    def toggle_rule(self):
        """Toggle selected auto-tag rule"""
        current_item = self.rules_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a rule to toggle.")
            return
            
        rule_id = current_item.data(0, Qt.UserRole)
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT enabled FROM auto_tag_rules WHERE id=%s", (rule_id,))
            result = cursor.fetchone()
            if not result:
                return
                
            new_status = not result[0]
            cursor.execute("UPDATE auto_tag_rules SET enabled=%s WHERE id=%s", (new_status, rule_id))
            conn.commit()
            
            self.load_rules()
            status_text = "enabled" if new_status else "disabled"
            self.update_status_bar(f"Rule {status_text}")
        finally:
            cursor.close()
            conn.close()

    def delete_rule(self):
        """Delete selected auto-tag rule"""
        current_item = self.rules_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a rule to delete.")
            return
            
        rule_id = current_item.data(0, Qt.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Delete the selected auto-tag rule?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM auto_tag_rules WHERE id=%s", (rule_id,))
                conn.commit()
                
                self.load_rules()
                self.update_status_bar("Rule deleted")
            finally:
                cursor.close()
                conn.close()

    def check_email_matches_rule(self, rule_type, operator, value, sender, subject, body):
        """Check if an email matches a specific rule"""
        try:
            target_text = ""
            
            if rule_type == 'sender':
                target_text = (sender or "").lower()
            elif rule_type == 'subject':
                target_text = (subject or "").lower()
            elif rule_type == 'body':
                target_text = (body or "").lower()
            elif rule_type == 'domain':
                if sender and '@' in sender:
                    try:
                        target_text = sender.split('@')[1].lower()
                    except IndexError:
                        target_text = ""
                else:
                    target_text = ""
            
            value_lower = (value or "").lower()
            
            if operator == 'contains':
                return value_lower in target_text
            elif operator == 'equals':
                return value_lower == target_text
            elif operator == 'starts_with':
                return target_text.startswith(value_lower)
            elif operator == 'ends_with':
                return target_text.endswith(value_lower)
            elif operator == 'regex':
                try:
                    return bool(re.search(value, target_text, re.IGNORECASE))
                except re.error:
                    return False
            
            return False
            
        except Exception as e:
            print(f"Error checking email rule match: {e}")
            return False

    def mark_selected_read(self):
        """Mark selected emails as read"""
        selected_items = self.email_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select emails to mark as read.")
            return
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            for item in selected_items:
                email_id = item.data(Qt.UserRole)
                cursor.execute("UPDATE emails SET read_status=TRUE WHERE id=%s", (email_id,))
            
            conn.commit()
            self.refresh_emails()
            self.update_status_bar(f"Marked {len(selected_items)} emails as read")
        finally:
            cursor.close()
            conn.close()

    def mark_selected_unread(self):
        """Mark selected emails as unread"""
        selected_items = self.email_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select emails to mark as unread.")
            return
            
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            for item in selected_items:
                email_id = item.data(Qt.UserRole)
                cursor.execute("UPDATE emails SET read_status=FALSE WHERE id=%s", (email_id,))
            
            conn.commit()
            self.refresh_emails()
            self.update_status_bar(f"Marked {len(selected_items)} emails as unread")
        finally:
            cursor.close()
            conn.close()

    def export_emails(self):
        """Export emails to file"""
        if not self.current_account_id:
            QMessageBox.warning(self, "No Account", "Please select an account first.")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Emails", 
            f"emails_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json);;CSV files (*.csv)"
        )
        
        if not filename:
            return
            
        QMessageBox.information(self, "Export", "Export functionality to be implemented.")

    def advanced_search(self):
        """Open advanced search dialog"""
        dialog = AdvancedSearchDialog(self, self.current_account_id)
        dialog.exec_()

    def search_attachments(self):
        """Open search attachments window"""
        from views.main.search_attachments_window import SearchAttachmentsWindow
        search_window = SearchAttachmentsWindow(self.user_id, self)
        search_window.show()

    def bulk_operations(self):
        """Open bulk operations dialog"""
        dialog = BulkOperationsDialog(self, self.current_account_id, self.user_id)
        dialog.exec_()

    def clean_duplicate_attachments(self):
        """Clean up duplicate attachment files and folders"""
        if not self.current_account_id:
            QMessageBox.warning(self, "No Account", "Please select an account first.")
            return
            
        dialog = AttachmentCleanupDialog(self, self.user_id)
        dialog.exec_()


    
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == dialog.Accepted:
            pass

    def animate_initial_progress(self):
        """Animate progress bar during initial phase"""
        if hasattr(self, 'progress_bar') and self.progress_bar and self.total_emails_to_process == 0:
            try:
                current_value = self.progress_bar.value()
                if current_value < 10:
                    self.progress_bar.setValue(current_value + 1)
                else:
                    self.progress_bar.setValue(0)
            except RuntimeError:
                pass
        else:
            if hasattr(self, 'progress_animation_timer'):
                self.progress_animation_timer.stop()

    def closeEvent(self, event):
        """Handle window closing - clean up threads"""
        # Stop all workers and release locks
        self.stop_all_workers()
        
        # Stop HTML worker if running
        if hasattr(self, 'html_worker') and self.html_worker and self.html_worker.thread.isRunning():
            try:
                self.html_worker.stop()
                self.html_worker.thread.wait(2000)  # Wait up to 2 seconds
            except Exception as e:
                print(f"Error stopping HTML worker: {e}")
        
        if hasattr(self, 'progress_dialog') and self.progress_dialog and self.progress_dialog.isVisible():
            try:
                self.progress_dialog.close()
            except:
                pass  # Ignore errors when closing dialog
            self.progress_dialog = None
        
        event.accept()

    # old logout method

    def logout(self):
        """Logout and return to login screen"""
        reply = QMessageBox.question(
            self, "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.stop_real_time_monitoring()
            self.cancel_sync()
            
            app = QApplication.instance()
            main_windows = [widget for widget in app.topLevelWidgets() 
                        if hasattr(widget, 'logout') and callable(getattr(widget, 'logout'))]
            
            if main_windows:
                main_windows[0].logout()
            else:
                self.close()

    # def logout(self):
    #     msg = QMessageBox()
    #     msg.setWindowTitle("Logout")
    #     msg.setText("Are you sure you want to logout?")

    #     # Remove default buttons
    #     msg.setStandardButtons(QMessageBox.NoButton)

    #     # Add custom buttons
    #     yes_btn = msg.addButton("Yes", QMessageBox.YesRole)
    #     no_btn = msg.addButton("No", QMessageBox.NoRole)

    #     # Apply blue style to buttons
    #     msg.setStyleSheet("""
    #         QPushButton {
    #             background-color: #0078D7;
    #             color: white;
    #             border-radius: 6px;
    #             padding: 5px 15px;
    #             font-weight: bold;
    #         }
    #         QPushButton:hover {
    #             background-color: #005A9E;
    #         }
    #     """)

    #     msg.exec_()

    #     if msg.clickedButton() == yes_btn:
    #         self.close()



    def animate_initial_progress(self):
        """Animate progress bar during initial phase"""
        if hasattr(self, 'progress_bar') and self.progress_bar and self.total_emails_to_process == 0:
            try:
                current_value = self.progress_bar.value()
                if current_value < 10:
                    self.progress_bar.setValue(current_value + 1)
                else:
                    self.progress_bar.setValue(0)
            except RuntimeError:
                pass
        else:
            # Stop animation once we have real progress
            if hasattr(self, 'progress_animation_timer'):
                self.progress_animation_timer.stop()

    def is_worker_running(self):
        """Check if any email fetch worker is currently running"""
        return (self.sync_worker and self.sync_worker.isRunning()) or \
               (self.auto_sync_worker and self.auto_sync_worker.isRunning()) or \
               self.worker_lock

    def set_worker_lock(self, locked=True):
        """Set or release the worker lock to prevent conflicts"""
        self.worker_lock = locked
        if locked:
            print("🔒 Worker lock acquired - preventing concurrent operations")
        else:
            print("🔓 Worker lock released - operations can proceed")

    def stop_all_workers(self):
        """Stop all running workers and release locks"""
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.stop()
            self.sync_worker.wait()
            
        if self.auto_sync_worker and self.auto_sync_worker.isRunning():
            self.auto_sync_worker.stop()
            self.auto_sync_worker.wait()
            
        if self.real_time_monitor:
            self.real_time_monitor.stop()
            
        self.set_worker_lock(False)
        print("🛑 All workers stopped and locks released")

    def _handle_auto_sync_error(self, *args):
        """Handle auto-sync error signal with robust argument processing"""
        try:
            # Handle variable arguments from Qt signal
            if len(args) == 0:
                error_message = "Auto-sync error (no arguments)"
            elif len(args) == 1:
                error_message = args[0]
            else:
                error_message = f"Auto-sync error with multiple args: {args}"
            
            print(f"DEBUG: _handle_auto_sync_error called with {len(args)} args: {args}")
            print(f"DEBUG: arg types: {[type(arg).__name__ for arg in args]}")
            
            # Call the actual error handler
            self.auto_sync_error(error_message)
            
        except Exception as e:
            print(f"Error in _handle_auto_sync_error: {e}")
            self.auto_sync_error("Auto-sync error (handler failed)")
        
    def auto_sync_error(self, error_message=None):
        """Handle auto-sync error silently"""
        try:
            # Ensure error_message is a string and handle all possible types
            if error_message is None:
                error_message = "Unknown auto-sync error occurred"
            elif isinstance(error_message, bool):
                error_message = "Auto-sync completed with issues" if error_message else "Auto-sync failed with no details"
            elif isinstance(error_message, (int, float)):
                error_message = f"Auto-sync error code: {error_message}"
            elif isinstance(error_message, (list, tuple)):
                error_message = f"Auto-sync error list: {', '.join(str(item) for item in error_message)}"
            elif not isinstance(error_message, str):
                error_message = str(error_message)
                
            self.update_status_bar("Auto-sync failed")
            print(f"Auto-sync error: {error_message}")
            
        except Exception as e:
            print(f"Error handling auto-sync error: {e}")
            self.update_status_bar("Auto-sync error occurred")
            
        # Release worker lock
        self.set_worker_lock(False)

    def _update_attachments_button_state(self, has_attachments):
        """Update the attachments button state and appearance"""
        self.attachments_btn.setEnabled(has_attachments)
        
        if has_attachments:
            self.attachments_btn.setToolTip("Click to view email attachments")
            self.attachments_btn.setText("View Attachments")
        else:
            self.attachments_btn.setToolTip("No attachments available for this email")
            self.attachments_btn.setText("No Attachments")

