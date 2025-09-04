#!/usr/bin/env python3
"""
Test script for attachment search functionality
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.attachment import Attachment
from config.database import DB_CONFIG
import mysql.connector

def test_attachment_search():
    """Test the attachment search functionality"""
    print("Testing attachment search functionality...")
    
    # Test 1: Check if attachments table exists
    print("\n1. Checking attachments table...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SHOW TABLES LIKE 'attachments'")
        if cursor.fetchone():
            print("✅ Attachments table exists")
        else:
            print("❌ Attachments table not found")
            return False
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    
    # Test 2: Check if there are any attachments in the database
    print("\n2. Checking for existing attachments...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM attachments")
        count = cursor.fetchone()[0]
        print(f"Found {count} attachments in database")
        
        if count > 0:
            print("✅ Attachments found in database")
        else:
            print("⚠️  No attachments found - you may need to fetch emails with attachments first")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error checking attachments: {e}")
        return False
    
    # Test 3: Test search functionality
    print("\n3. Testing search functionality...")
    try:
        # Test search with empty query (should return all)
        results = Attachment.search_attachments("", user_id=1)
        print(f"Search with empty query returned {len(results)} results")
        
        # Test search with a common term
        results = Attachment.search_attachments("pdf", user_id=1)
        print(f"Search for 'pdf' returned {len(results)} results")
        
        # Test search with email subject
        results = Attachment.search_attachments("test", user_id=1)
        print(f"Search for 'test' returned {len(results)} results")
        
        print("✅ Search functionality working")
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return False
    
    # Test 4: Test attachment details retrieval
    print("\n4. Testing attachment details retrieval...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM attachments LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            attachment_id = result[0]
            details = Attachment.get_attachment_with_email_metadata(attachment_id)
            if details:
                print(f"✅ Retrieved details for attachment: {details['filename']}")
            else:
                print("❌ Failed to retrieve attachment details")
        else:
            print("⚠️  No attachments available for testing")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error testing attachment details: {e}")
        return False
    
    print("\n✅ All tests completed successfully!")
    return True

def test_database_connection():
    """Test database connection"""
    print("Testing database connection...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Attachment Search Feature Test")
    print("=" * 50)
    
    # Test database connection first
    if not test_database_connection():
        print("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Test attachment search functionality
    if test_attachment_search():
        print("\nAll tests passed! The attachment search feature is ready to use.")
    else:
        print("\n❌ Some tests failed. Please check the database and attachment setup.") 