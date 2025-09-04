#!/usr/bin/env python3
"""
Test script for email verification functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.auth_controller import AuthController
from models.user import User

def test_verification_flow():
    """Test the complete email verification flow"""
    print("Testing Email Verification Flow")
    print("=" * 40)
    
    # Test data
    test_username = "testuser_verification"
    test_email = "test@example.com"
    test_password = "TestPass123!"
    
    print(f"1. Testing user registration...")
    success, message, user = AuthController.register_user(test_username, test_email, test_password)
    print(f"   Result: {success}")
    print(f"   Message: {message}")
    
    if success:
        print(f"\n2. Testing verification email sending...")
        email_success, email_message = AuthController.send_verification_email(test_email)
        print(f"   Result: {email_success}")
        print(f"   Message: {email_message}")
        
        if email_success:
            print(f"\n3. Testing verification code generation...")
            code = User.generate_verification_code(test_email)
            print(f"   Generated code: {code}")
            
            if code:
                print(f"\n4. Testing verification with correct code...")
                verify_success, verify_message = AuthController.verify_user_email(test_email, code)
                print(f"   Result: {verify_success}")
                print(f"   Message: {verify_message}")
                
                print(f"\n5. Testing verification with wrong code...")
                wrong_success, wrong_message = AuthController.verify_user_email(test_email, "000000")
                print(f"   Result: {wrong_success}")
                print(f"   Message: {wrong_message}")
                
                print(f"\n6. Testing user verification status...")
                is_verified = User.is_user_verified(test_email)
                print(f"   User verified: {is_verified}")
    
    print("\n" + "=" * 40)
    print("Test completed!")

if __name__ == "__main__":
    test_verification_flow() 