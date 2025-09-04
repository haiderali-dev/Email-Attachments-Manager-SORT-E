#!/usr/bin/env python3
"""
Demo script for the new attachment search feature
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from views.main.search_attachments_window import SearchAttachmentsWindow

def demo_attachment_search():
    """Demo the attachment search window"""
    app = QApplication(sys.argv)
    
    # Create and show the search attachments window
    # Note: You need to be logged in with a valid user_id
    search_window = SearchAttachmentsWindow(user_id=1)  # Replace with actual user ID
    search_window.show()
    
    print("Attachment Search Demo")
    print("=" * 40)
    print("Features demonstrated:")
    print("✅ Search across multiple domains:")
    print("   - Filename (e.g., 'report.pdf')")
    print("   - Email subject (e.g., 'invoice')")
    print("   - Sender (e.g., 'john@company.com')")
    print("   - Email body content")
    print("   - File type (e.g., 'pdf', 'docx')")
    print("   - Domain (e.g., 'company.com')")
    print()
    print("✅ Search results show:")
    print("   - Filename and size")
    print("   - Email subject and sender")
    print("   - Date and account information")
    print()
    print("✅ Click on any result to see:")
    print("   - Complete attachment metadata")
    print("   - Full email information")
    print("   - Other attachments from same email")
    print("   - View and download options")
    print()
    print("💡 Try searching for:")
    print("   - File extensions: 'pdf', 'docx', 'xlsx'")
    print("   - Common terms: 'invoice', 'report', 'contract'")
    print("   - Email domains: 'gmail.com', 'outlook.com'")
    print("   - Sender names or email addresses")
    
    return app.exec_()

if __name__ == "__main__":
    demo_attachment_search() 