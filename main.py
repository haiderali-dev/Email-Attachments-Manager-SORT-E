import sys
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore
from views.main.main_application import MainApplication
from config.migrate_attachments import migrate_existing_attachments

def main():
    """Main application entry point"""
    
    # Set high DPI scaling before creating QApplication
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    
    # Set up error handling for Qt warnings
    import sys
    from PyQt5.QtCore import QCoreApplication
    
    # Suppress Qt warnings about CSS parsing and font issues
    QCoreApplication.setAttribute(QtCore.Qt.AA_DisableWindowContextHelpButton)
    
    app = QApplication(sys.argv)

    # Apply stylesheet with error handling
    try:
        app.setStyleSheet("""
        QMessageBox QPushButton {
            background-color: #4299e1;
            color: white;
            border-radius: 6px;
            padding: 6px 12px;
        }
        QMessageBox QPushButton:hover {
            background-color: #2b6cb0;
        }
        """)
    except Exception as e:
        print(f"Warning: Stylesheet application failed: {e}")
        # Continue without custom stylesheet
    
    
    # Set application properties
    app.setApplicationName("Email Management System")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Email Dashboard Inc.")
    
    # Initialize logging
    try:
        from utils.logger import app_logger
        app_logger.log_application_start()
    except Exception as e:
        print(f"Warning: Logging initialization failed: {e}")
    
    # Migrate existing attachments to database (non-blocking)
    try:
        migrate_existing_attachments()
    except Exception as e:
        print(f"Warning: Attachment migration failed: {e}")
        if 'app_logger' in locals():
            app_logger.log_error(e, "Attachment migration")
    
    # Initialize database connection pool
    try:
        from services.database_pool import db_pool
        print("✓ Database connection pool initialized")
        
        # Run database migrations to ensure schema is up to date
        try:
            from utils.database_migration import migrate_database
            migrate_database()
        except Exception as e:
            print(f"⚠ Database migration failed: {e}")
            
    except Exception as e:
        print(f"⚠ Database connection pool not available: {e}")
        db_pool = None
    
    # Create and show main window
    main_window = MainApplication()
    main_window.show()
    
    # Run application
    try:
        sys.exit(app.exec_())
    finally:
        if 'app_logger' in locals():
            app_logger.log_application_stop()

if __name__ == '__main__':
    main()
