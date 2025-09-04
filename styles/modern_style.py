from PyQt5.QtCore import QSize

class ModernStyle:
    @staticmethod
    def get_stylesheet():
        return """
        QMainWindow {
            background-color: #f0f2f5;
            color: #343C48;
        }
        
        QWidget {
            background-color: #ffffff;
            color: #343C48;
            font-family: 'Segoe UI', Arial, sans-serif;
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

QPushButton:disabled {
    background-color: #d1d5d9;
    color: #343C48;
}

/* Variants all follow same blue theme */
QPushButton.danger,
QPushButton.success,
QPushButton.warning {
    background-color: #3182ce;
    color: white;
}

QPushButton.danger:hover,
QPushButton.success:hover,
QPushButton.warning:hover {
    background-color: #2a4365;
}

QPushButton.danger:pressed,
QPushButton.success:pressed,
QPushButton.warning:pressed {
    background-color: #1e3250;
}
        
        QLineEdit, QTextEdit, QComboBox, QSpinBox {
            border: 2px solid #d1d5d9;
            padding: 8px;
            border-radius: 6px;
            background-color: #ffffff;
            color: #343C48;
        }
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
            border-color: #343C48;
            background-color: #ffffff;
            border-width: 3px;
        }
        
        QGroupBox {
            font-weight: 600;
            border: 2px solid #d1d5d9;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 10px;
            color: #343C48;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 10px 0 10px;
            background-color: #f0f2f5;
            color: #343C48;
        }
        
        QListWidget, QTreeWidget, QTableWidget {
            border: 1px solid #d1d5d9;
            alternate-background-color: #f8f9fa;
            background-color: #ffffff;
            selection-background-color: #e3e6ea;
            border-radius: 4px;
        }
        
        QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {
            background-color: #343C48;
            color: white;
            border-radius: 3px;
        }
        
        QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {
            background-color: #e3e6ea;
            color: #343C48;
        }
        
        QHeaderView::section {
            background-color: #e9ecef;
            padding: 8px;
            border: 1px solid #d1d5d9;
            font-weight: 600;
            color: #343C48;
        }
        
        QTabWidget::pane {
            border: 1px solid #d1d5d9;
            background-color: #ffffff;
            border-radius: 6px;
        }
        
        QTabBar::tab {
            background-color: #e9ecef;
            padding: 10px 18px;
            margin-right: 3px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            color: #343C48;
            font-weight: 500;
        }
        
        QTabBar::tab:selected {
            background-color: #ffffff;
            border-bottom: 3px solid #343C48;
            color: #343C48;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #e3e6ea;
        }
        
        QProgressBar {
            border: 1px solid #d1d5d9;
            border-radius: 6px;
            text-align: center;
            background-color: #ffffff;
            color: #343C48;
        }
        
        QProgressBar::chunk {
            background-color: #343C48;
            border-radius: 5px;
        }
        
        QStatusBar {
            background-color: #f0f2f5;
            border-top: 1px solid #d1d5d9;
            color: #343C48;
        }
        
        QMenuBar {
            background-color: #f0f2f5;
            border-bottom: 1px solid #d1d5d9;
            color: #343C48;
            padding: 4px;
        }
        
        QMenuBar::item {
            padding: 6px 12px;
            border-radius: 4px;
        }
        
        QMenuBar::item:selected {
            background-color: #e3e6ea;
            color: #343C48;
        }
        
        QMenu {
            background-color: #ffffff;
            border: 1px solid #d1d5d9;
            border-radius: 6px;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 6px 12px;
            border-radius: 4px;
            color: #343C48;
        }
        
        QMenu::item:selected {
            background-color: #343C48;
            color: white;
        }
        
        QScrollBar:vertical {
            background-color: #f0f2f5;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #b8bcc2;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #343C48;
        }
        
        QScrollBar:horizontal {
            background-color: #f0f2f5;
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #b8bcc2;
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #343C48;
        }
        
        QToolTip {
            background-color: #343C48;
            color: white;
            border: 1px solid #343C48;
            border-radius: 4px;
            padding: 4px;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #d1d5d9;
            height: 6px;
            background: #e9ecef;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background: #343C48;
            border: 2px solid #343C48;
            width: 16px;
            height: 16px;
            border-radius: 8px;
            margin: -5px 0;
        }
        
        QSlider::handle:horizontal:hover {
            background: #2a313a;
        }
        """

    @staticmethod
    def get_responsive_size(base_size, screen_size):
        """Calculate responsive size based on screen resolution"""
        width_factor = screen_size.width() / 1920.0  # Base on 1920x1080
        height_factor = screen_size.height() / 1080.0
        
        factor = min(width_factor, height_factor)
        factor = max(0.7, min(1.3, factor))  # Limit scaling between 70% and 130%
        
        return QSize(int(base_size.width() * factor), int(base_size.height() * factor))