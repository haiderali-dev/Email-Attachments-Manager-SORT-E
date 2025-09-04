from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5 import QtWidgets
from PyQt5.QtCore import QSize, QTimer
from PyQt5.QtGui import QKeySequence
from styles.modern_style import ModernStyle
from views.auth.login_window import LoginWindow
from views.auth.register_window import RegisterWindow
from views.auth.forgot_window import ForgotWindow
from views.auth.reset_window import ResetWindow
from views.auth.verification_window import VerificationWindow
from views.main.email_management_window import EmailManagementWindow

class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user_id = None
        
        # Performance optimization
        self._apply_performance_optimizations()
        self.init_ui()
        
        # Defer heavy operations
        QTimer.singleShot(50, self._deferred_setup)

    def _deferred_setup(self):
        """Deferred setup to avoid blocking UI"""
        try:
            # Apply modern styling with error handling
            try:
                self.setStyleSheet(ModernStyle.get_stylesheet())
            except Exception as e:
                print(f"Warning: Modern style application failed: {e}")
                # Continue without custom styling
        except Exception as e:
            print(f"Deferred setup error: {e}")

    def _apply_performance_optimizations(self):
        """Apply performance optimizations to the main window"""
        try:
            # Import performance systems with error handling
            performance_optimizer = None
            ui_optimizer = None
            
            try:
                from utils.performance_optimizer import performance_optimizer
            except ImportError:
                print("⚠ Performance optimizer not available")
            
            try:
                from utils.ui_optimizer import ui_optimizer
            except ImportError:
                print("⚠ UI optimizer not available")
            
            # Register for optimization if available
            if ui_optimizer:
                try:
                    ui_optimizer.register_widget(self, 'main_window')
                    
                    # Apply rendering optimizations
                    ui_optimizer.optimize_rendering(self)
                    print("✓ Main window performance optimization applied")
                except Exception as e:
                    print(f"⚠ UI optimization setup failed: {e}")
            else:
                print("⚠ UI optimization skipped - optimizer not available")
                
        except Exception as e:
            print(f"⚠ Performance optimization setup failed: {e}")
            print("⚠ Application will continue without performance optimizations")

    def init_ui(self):
        self.setWindowTitle("Email Management System")
        
        # Get screen size for responsive design
        screen = QApplication.desktop().screenGeometry()
        # Use fixed size to prevent vertical stretching
        window_size = QSize(600, 700)
        # Ensure window doesn't exceed screen bounds
        if window_size.width() > screen.width():
            window_size.setWidth(screen.width() - 100)
        if window_size.height() > screen.height():
            window_size.setHeight(screen.height() - 100)
        self.resize(window_size)
        
        # Set minimum window size to prevent window from being too small
        self.setMinimumSize(500, 600)
        
        # Center window
        self.move(screen.center() - self.rect().center())
        
        # Create stacked widget for different screens
        self.stacked_widget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create dashboard login stack
        self.login_stack = QtWidgets.QStackedWidget()
        
        # Create login windows (deferred creation for better performance)
        self._create_login_windows()
        
        # Add login stack to main stacked widget
        self.stacked_widget.addWidget(self.login_stack)
        
        # Set login window as the initial view
        self.stacked_widget.setCurrentWidget(self.login_stack)
        
        # Connect login successful signal
        self.login_window.login_successful.connect(self.open_email_management)
        
        # Connect register window to create verification window
        self.register_window.verification_needed.connect(self.show_verification_window)
        
        # Add full screen toggle shortcut (F11)
        self.fullscreen_shortcut = QtWidgets.QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

    def open_email_management(self, user_id):
        """Open email management window after successful login"""
        self.current_user_id = user_id
        
        # Show loading message
        self.setWindowTitle("Email Management System - Loading...")
        
        # Create email management window (deferred for better performance)
        QTimer.singleShot(100, lambda: self._create_email_window(user_id))
        
        # Expand window for email management
        screen = QApplication.desktop().screenGeometry()
        # Use fixed size to prevent vertical stretching
        window_size = QSize(1400, 900)
        # Ensure window doesn't exceed screen bounds
        if window_size.width() > screen.width():
            window_size.setWidth(screen.width() - 100)
        if window_size.height() > screen.height():
            window_size.setHeight(screen.height() - 100)
        self.resize(window_size)
        
        # Set minimum window size for email management
        self.setMinimumSize(800, 600)
        
        self.move(screen.center() - self.rect().center())
        
        # Update window title after initialization
        QTimer.singleShot(2000, lambda: self.setWindowTitle("Email Management System"))

    def _create_email_window(self, user_id):
        """Create email management window with performance optimization"""
        try:
            # Create email management window
            self.email_window = EmailManagementWindow(user_id)
            
            # Add to stacked widget and switch to it immediately
            self.stacked_widget.addWidget(self.email_window)
            self.stacked_widget.setCurrentWidget(self.email_window)
            
        except Exception as e:
            print(f"Email window creation error: {e}")
            self.setWindowTitle("Email Management System - Error")

    def closeEvent(self, event):
        """Handle application closing with cleanup"""
        try:
            # If email window is open, give it a chance to clean up
            if hasattr(self, 'email_window'):
                # The EmailManagementWindow has its own closeEvent handler
                pass
            
            # Cleanup performance systems
            try:
                from utils.ui_optimizer import ui_optimizer
                ui_optimizer.unregister_widget(self)
            except:
                pass
                
        except Exception as e:
            print(f"Close event error: {e}")
        
        event.accept()

    def logout(self):
        """Return to login screen"""
        if hasattr(self, 'email_window'):
            # Clean up email window
            self.email_window.close()  # This will trigger its closeEvent
            self.stacked_widget.removeWidget(self.email_window)
            self.email_window.deleteLater()
            del self.email_window
        
        self.stacked_widget.setCurrentWidget(self.login_stack)
        self.current_user_id = None
        
        # Resize back to login size
        screen = QApplication.desktop().screenGeometry()
        # Use fixed size to prevent vertical stretching
        window_size = QSize(600, 700)
        # Ensure window doesn't exceed screen bounds
        if window_size.width() > screen.width():
            window_size.setWidth(screen.width() - 100)
        if window_size.height() > screen.height():
            window_size.setHeight(screen.height() - 100)
        self.resize(window_size)
        
        # Reset window size constraints for login
        self.setMinimumSize(500, 600)
        
        self.move(screen.center() - self.rect().center())

    def show_verification_window(self, email: str):
        """Show verification window for email verification"""
        # Remove existing verification window if it exists
        if self.verification_window:
            self.login_stack.removeWidget(self.verification_window)
            self.verification_window.deleteLater()
        
        # Create new verification window with email
        self.verification_window = VerificationWindow(self.login_stack, email)
        self.login_stack.addWidget(self.verification_window)  # index 4
        
        # Switch to verification window
        self.login_stack.setCurrentIndex(4)

    def _create_login_windows(self):
        """Create login windows with performance optimization"""
        try:
            # Create windows
            self.login_window = LoginWindow(self.login_stack)
            self.register_window = RegisterWindow(self.login_stack)
            self.forgot_window = ForgotWindow(self.login_stack)
            self.reset_window = ResetWindow(self.login_stack)
            
            # Add windows to login stack
            self.login_stack.addWidget(self.login_window)      # index 0
            self.login_stack.addWidget(self.register_window)   # index 1
            self.login_stack.addWidget(self.forgot_window)     # index 2
            self.login_stack.addWidget(self.reset_window)      # index 3
            
            # Create verification window (will be added dynamically with email)
            self.verification_window = None
            
        except Exception as e:
            print(f"Login window creation error: {e}")
    
    def toggle_fullscreen(self):
        """Toggle between full screen and normal window mode"""
        if self.isFullScreen():
            self.showNormal()
            # Restore previous window size if available
            if hasattr(self, 'previous_geometry'):
                self.setGeometry(self.previous_geometry)
        else:
            # Save current geometry before going full screen
            self.previous_geometry = self.geometry()
            self.showFullScreen()