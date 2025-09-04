import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional, Tuple
from models.user import User
from config.settings import PASSWORD_REGEX, EMAIL_CONFIG

class AuthController:
    """Authentication business logic controller"""
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Validate password against security requirements
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not password:
            return False, "Password cannot be empty"
            
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
            
        if not PASSWORD_REGEX.match(password):
            return False, ("Password must include:\n"
                         "• Uppercase and lowercase letters\n"
                         "• At least one number\n"
                         "• At least one special character")
        
        return True, ""

    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> Optional[User]:
        """
        Authenticate user with username/email and password
        
        Args:
            username_or_email: Username or email address
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        if not username_or_email or not password:
            return None
            
        return User.authenticate(username_or_email, password)

    @staticmethod
    def register_user(username: str, email: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user (unverified)
        
        Args:
            username: Username for the account
            email: Email address
            password: Plain text password
            
        Returns:
            Tuple[bool, str, Optional[User]]: (success, message, user_object)
        """
        # Validate input
        if not username or not email or not password:
            return False, "All fields are required", None
            
        # Validate password
        is_valid, error_msg = AuthController.validate_password(password)
        if not is_valid:
            return False, error_msg, None
            
        # Validate email format (basic)
        if '@' not in email or '.' not in email:
            return False, "Please enter a valid email address", None
            
        # Create user (unverified)
        user = User.create_user(username, email, password)
        if user:
            return True, "Account created! Please check your email for verification code.", user
        else:
            return False, "Username or email already exists", None

    @staticmethod
    def send_verification_email(email: str) -> Tuple[bool, str]:
        """
        Send verification email with code
        
        Args:
            email: Email address to send verification to
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not email:
            return False, "Email address is required"
            
        # Generate verification code
        code = User.generate_verification_code(email)
        if not code:
            return False, "No account found with this email address"
            
        # Send email
        try:
            msg = EmailMessage()
            msg['Subject'] = 'Email Verification Code - Email Dashboard'
            msg['From'] = EMAIL_CONFIG['username']
            msg['To'] = email
            
            msg.set_content(
                f"Your email verification code is: {code}\n"
                f"This code expires in 15 minutes.\n\n"
                f"If you did not request this, please ignore this email."
            )
            
            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <h2 style="color: #0078d4; text-align: center;">📧 Email Verification</h2>
                    <p>Thank you for registering with the Email Dashboard. Use the verification code below to complete your registration:</p>
                    <div style="text-align: center; background-color: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; color: #0078d4; letter-spacing: 4px;">{code}</span>
                    </div>
                    <p><strong>Expires in:</strong> 15 minutes</p>
                    <p style="color: #666; font-size: 14px;">If you did not request this, please ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #666; font-size: 12px; text-align: center;">Email Management Dashboard</p>
                </div>
            </body>
            </html>
            """
            msg.add_alternative(html_content, subtype='html')

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], context=context
            ) as server:
                server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
                server.send_message(msg)
                
            return True, "Verification code sent to your email. Please check your inbox."
            
        except Exception as ex:
            return False, f"Failed to send email: {str(ex)}"

    @staticmethod
    def verify_user_email(email: str, code: str) -> Tuple[bool, str]:
        """
        Verify user email with verification code
        
        Args:
            email: Email address
            code: Verification code from email
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not email or not code:
            return False, "Email and verification code are required"
            
        # Verify user
        success = User.verify_user(email, code)
        if success:
            return True, "Email verified successfully! You can now log in to your account."
        else:
            return False, "Invalid or expired verification code. Please try again."

    @staticmethod
    def send_password_reset_email(email: str) -> Tuple[bool, str]:
        """
        Send password reset email with PIN
        
        Args:
            email: Email address to send reset to
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not email:
            return False, "Email address is required"
            
        # Generate reset token
        token = User.generate_reset_token(email)
        if not token:
            return False, "No account found with this email address"
            
        # Send email
        try:
            msg = EmailMessage()
            msg['Subject'] = 'Password Reset PIN - Email Dashboard'
            msg['From'] = EMAIL_CONFIG['username']
            msg['To'] = email
            
            msg.set_content(
                f"Your password reset PIN is: {token}\n"
                f"This PIN expires in 20 minutes.\n\n"
                f"If you did not request this, please ignore this email."
            )
            
            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <h2 style="color: #0078d4; text-align: center;">🔑 Password Reset Request</h2>
                    <p>You requested to reset your password for the Email Dashboard. Use the PIN below to proceed:</p>
                    <div style="text-align: center; background-color: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; color: #0078d4; letter-spacing: 4px;">{token}</span>
                    </div>
                    <p><strong>Expires in:</strong> 20 minutes</p>
                    <p style="color: #666; font-size: 14px;">If you did not request this, please ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #666; font-size: 12px; text-align: center;">Email Management Dashboard</p>
                </div>
            </body>
            </html>
            """
            msg.add_alternative(html_content, subtype='html')

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], context=context
            ) as server:
                server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
                server.send_message(msg)
                
            return True, "A 4-digit PIN has been sent to your email. Please check your inbox and proceed to reset your password."
            
        except Exception as ex:
            return False, f"Failed to send email: {str(ex)}"

    @staticmethod
    def reset_password(email: str, token: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset password using token and new password
        
        Args:
            email: Email address
            token: Reset token from email
            new_password: New password
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not email or not token or not new_password:
            return False, "All fields are required"
            
        # Validate new password
        is_valid, error_msg = AuthController.validate_password(new_password)
        if not is_valid:
            return False, error_msg
            
        # Reset password
        success = User.reset_password(email, token, new_password)
        if success:
            return True, "Password reset successfully! Please log in with your new password."
        else:
            return False, "Invalid or expired PIN. Please try again."

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User object if found, None otherwise
        """
        return User.get_by_id(user_id)

    @staticmethod
    def is_account_locked(username_or_email: str) -> Tuple[bool, str]:
        """
        Check if account is locked due to failed attempts
        
        Args:
            username_or_email: Username or email to check
            
        Returns:
            Tuple[bool, str]: (is_locked, lock_message)
        """
        user = User.get_by_id(username_or_email)
        if not user:
            return False, ""
            
        if user.locked_until:
            return True, f"Account locked until {user.locked_until}"
            
        return False, "" 