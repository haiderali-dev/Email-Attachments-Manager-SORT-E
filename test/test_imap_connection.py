#!/usr/bin/env python3
"""
IMAP Connection Diagnostic Tool
This script helps diagnose email server connection issues
"""

import sys
import os
import ssl
import socket
from imap_tools import MailBox
from config.settings import CONFIG

def test_network_connectivity(host, port=993):
    """Test basic network connectivity to the IMAP server"""
    print(f"Testing network connectivity to {host}:{port}")
    
    try:
        # Test basic socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Network connectivity: SUCCESS")
            return True
        else:
            print(f"❌ Network connectivity: FAILED (Error code: {result})")
            return False
            
    except Exception as e:
        print(f"❌ Network connectivity: ERROR - {e}")
        return False

def test_ssl_connection(host, port=993):
    """Test SSL connection to the IMAP server"""
    print(f"Testing SSL connection to {host}:{port}")
    
    try:
        # Test SSL connection
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                print(f"✅ SSL connection: SUCCESS")
                print(f"   SSL Version: {ssock.version()}")
                print(f"   Cipher: {ssock.cipher()[0]}")
                return True
                
    except Exception as e:
        print(f"❌ SSL connection: ERROR - {e}")
        return False

def test_imap_connection(host, email, password):
    """Test IMAP login with provided credentials"""
    print(f"📧 Testing IMAP login to {host}")
    print(f"   Email: {email}")
    
    try:
        # Test IMAP connection and login
        with MailBox(host).login(email, password, 'INBOX') as mailbox:
            print(f"✅ IMAP login: SUCCESS")
            
            # Get some basic info
            try:
                messages = list(mailbox.fetch(limit=1))
                print(f"   Messages in inbox: {len(messages)}")
            except Exception as e:
                print(f"   Warning: Could not fetch messages - {e}")
            
            return True
            
    except Exception as e:
        print(f"❌ IMAP login: ERROR - {e}")
        return False

def main():
    """Main diagnostic function"""
    print("IMAP Connection Diagnostic Tool")
    print("=" * 50)
    
    # Get configuration
    imap_host = CONFIG.get('default_imap_host', 'mail2.multinet.com.pk')
    print(f"IMAP Host: {imap_host}")
    
    # Test network connectivity
    if not test_network_connectivity(imap_host):
        print("\n💡 Troubleshooting tips:")
        print("   • Check your internet connection")
        print("   • Verify the IMAP host is correct")
        print("   • Try using a different IMAP port (143 for non-SSL)")
        return
    
    # Test SSL connection
    if not test_ssl_connection(imap_host):
        print("\n💡 Troubleshooting tips:")
        print("   • The server might not support SSL")
        print("   • Try using port 143 (non-SSL)")
        print("   • Check if the server requires STARTTLS")
        return
    
    # Test IMAP login (if credentials are provided)
    print("\n" + "=" * 50)
    print("📝 To test IMAP login, please provide your email credentials:")
    
    try:
        email = input("Email address: ").strip()
        if not email:
            print("No email provided. Skipping IMAP login test.")
            return
            
        password = input("Password: ").strip()
        if not password:
            print("No password provided. Skipping IMAP login test.")
            return
        
        print()
        test_imap_connection(imap_host, email, password)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Error during login test: {e}")
    
    print("\n" + "=" * 50)
    print("🔧 Additional troubleshooting steps:")
    print("1. Verify your email server settings:")
    print(f"   • IMAP Host: {imap_host}")
    print("   • IMAP Port: 993 (SSL) or 143 (non-SSL)")
    print("   • Username: Your full email address")
    print("   • Password: Your email password or app password")
    print()
    print("2. Common issues:")
    print("   • Enable 'Less secure app access' in Gmail")
    print("   • Use an App Password instead of your main password")
    print("   • Check if 2FA is enabled and use an app password")
    print("   • Verify the IMAP server is correct for your email provider")
    print()
    print("3. Email provider specific settings:")
    print("   • Gmail: imap.gmail.com:993")
    print("   • Outlook: outlook.office365.com:993")
    print("   • Yahoo: imap.mail.yahoo.com:993")

if __name__ == "__main__":
    main()
