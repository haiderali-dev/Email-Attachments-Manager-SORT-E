#!/usr/bin/env python3
"""
Simple test script for user to test date range filter
Run this script and follow the instructions to test the date range filter
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore
from views.main.email_management_window import EmailManagementWindow

def test_date_filter():
    """Simple test for date range filter"""
    print("🧪 Testing Date Range Filter - User Version")
    print("=" * 50)
    print("Instructions:")
    print("1. The application window will open")
    print("2. Select an email account from the dropdown")
    print("3. Change the filter dropdown to 'Date Range'")
    print("4. Set a date range using the date pickers")
    print("5. Check if emails are displayed")
    print("6. Look for debug messages in the console")
    print("7. Close the window when done")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    try:
        window = EmailManagementWindow(user_id=1)
        window.show()
        
        print("\n✅ Application started successfully!")
        print("Debug messages will appear in the console as you use the date range filter")
        print("Please test the date range filter and report any issues")
        
        # Start the event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_date_filter() 