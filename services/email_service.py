import re
import email
import email.policy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.application import MIMEApplication
from email import encoders
import base64
import quopri
import mimetypes
import os
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
import mysql.connector
from config.database import DB_CONFIG
from models.email import Email
from models.rule import AutoTagRule
from services.attachment_service import AttachmentService
from utils.helpers import get_safe_filename
from utils.validators import validate_email_rfc_compliant, validate_imap_host_enhanced
from services.encryption_service import decrypt_text
from imap_tools import MailBox

class EmailService:
    """Enhanced email fetching and processing service with proper MIME parsing"""

    def __init__(self):
        self.attachment_service = AttachmentService()
        self.should_stop = False

    def fetch_emails(self, imap_host: str, imap_port: int, email: str, password: str, 
                    account_id: int, user_id: int, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Fetch emails from IMAP server with enhanced MIME parsing
        
        Args:
            imap_host: IMAP server host
            imap_port: IMAP server port
            email: Email address
            password: Email password
            account_id: Database account ID
            user_id: Database user ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with results: {'success': bool, 'new_count': int, 'error': str}
        """
        self.should_stop = False
        
        try:
            if progress_callback:
                progress_callback("Connecting to email server...")
            
            with MailBox(imap_host, port=imap_port).login(email, password, 'INBOX') as mailbox:
                if self.should_stop:
                    return {'success': False, 'new_count': 0, 'error': 'Operation cancelled'}
                    
                if progress_callback:
                    progress_callback("Fetching ALL emails...")
                
                # Get ALL emails (no limit) for progressive processing
                messages = list(mailbox.fetch(reverse=True))
                
                if not messages:
                    if progress_callback:
                        progress_callback("No emails found")
                    return {'success': True, 'new_count': 0, 'error': None}
                
                new_count = 0
                total_messages = len(messages)
                
                if progress_callback:
                    progress_callback(f"Found {total_messages} emails to process")
                
                for i, msg in enumerate(messages):
                    if self.should_stop:
                        break
                        
                    try:
                        if progress_callback:
                            progress_callback(f"Processing email {i+1}/{total_messages}")
                        
                        # Process email with enhanced MIME parsing
                        result = self._process_email(msg, account_id, user_id)
                        if result:
                            new_count += 1
                            
                    except Exception as e:
                        print(f"Error processing email {i+1}: {e}")
                        continue
                
                if progress_callback:
                    progress_callback(f"Completed! {new_count} new emails processed")
                
                return {'success': True, 'new_count': new_count, 'error': None}
                
        except Exception as e:
            error_msg = f"Failed to fetch emails: {e}"
            print(error_msg)
            if progress_callback:
                progress_callback(f"Error: {error_msg}")
            return {'success': False, 'new_count': 0, 'error': error_msg}

    def _process_email(self, msg, account_id: int, user_id: int) -> bool:
        """
        Process a single email message with proper MIME parsing
        
        Args:
            msg: Email message object
            account_id: Database account ID
            user_id: Database user ID
            
        Returns:
            True if email was processed successfully, False otherwise
        """
        try:
            uid = str(msg.uid) if msg.uid else f"no_uid_{id(msg)}"
            subject = msg.subject or "(No subject)"
            sender = str(msg.from_) if msg.from_ else "(Unknown sender)"
            recipients = ", ".join([str(addr) for addr in msg.to]) if msg.to else ""
            date = msg.date
            
            # Enhanced MIME parsing for email body
            body_text, body_html, body_format, inline_images = self._parse_mime_content(msg)
            
            # For backward compatibility, set body to text or HTML
            body = body_text or body_html or ""
            
            # Debug logging for MIME parsing
            if body_html:
                print(f"✅ HTML email parsed: {subject[:30]}... (Format: {body_format})")
            if inline_images:
                print(f"🖼️ Found {len(inline_images)} inline images in: {subject[:30]}...")
            
            # Calculate size based on total content
            total_content = (body_text or "") + (body_html or "")
            size_bytes = len(total_content.encode('utf-8')) if total_content else 0
            has_attachment = bool(msg.attachments) if hasattr(msg, 'attachments') else False
            
            # Check if email already exists
            existing_email = Email.get_by_id(uid)
            if existing_email:
                # Email exists - only apply auto-tags if needed
                self._apply_auto_tags_safe(existing_email.id, sender, subject, body, 
                                         msg.attachments if hasattr(msg, 'attachments') else [],
                                         user_id)
                return False  # Not a new email
            
            # Insert new email with enhanced body format support
            email = Email.create_email(
                uid=uid,
                subject=subject,
                sender=sender,
                recipients=recipients,
                date=date,
                has_attachment=has_attachment,
                body=body,
                body_text=body_text,
                body_html=body_html,
                body_format=body_format,
                size_bytes=size_bytes,
                account_id=account_id
            )
            
            if email:
                # Apply auto-tags
                self._apply_auto_tags_safe(email.id, sender, subject, body, 
                                         msg.attachments if hasattr(msg, 'attachments') else [],
                                         user_id)
                return True
            
        except Exception as e:
            print(f"Error processing email: {e}")
            return False
        
        return False

    def _parse_mime_content(self, msg) -> Tuple[str, str, str, List[Dict[str, Any]]]:
        """
        Parse MIME content from email message with proper content type detection
        
        Args:
            msg: Email message object
            
        Returns:
            Tuple of (body_text, body_html, body_format, inline_images)
        """
        body_text = ""
        body_html = ""
        body_format = 'text'
        inline_images = []
        
        try:
            # Handle different message types
            if hasattr(msg, 'obj') and msg.obj:
                # Use the parsed message object if available
                parsed_msg = msg.obj
            else:
                # Parse the raw message
                raw_message = msg.obj if hasattr(msg, 'obj') else str(msg)
                parsed_msg = email.message_from_string(raw_message, policy=email.policy.default)
            
            # Parse MIME parts
            body_text, body_html, body_format, inline_images = self._parse_mime_parts(parsed_msg)
            
            # Fallback to basic extraction if MIME parsing fails
            if not body_text and not body_html:
                body_text, body_html, body_format = self._fallback_content_extraction(msg)
                
        except Exception as e:
            print(f"MIME parsing failed, using fallback: {e}")
            body_text, body_html, body_format = self._fallback_content_extraction(msg)
        
        return body_text, body_html, body_format, inline_images

    def _parse_mime_parts(self, parsed_msg) -> Tuple[str, str, str, List[Dict[str, Any]]]:
        """
        Parse MIME multipart message structure
        
        Args:
            parsed_msg: Parsed email message
            
        Returns:
            Tuple of (body_text, body_html, body_format, inline_images)
        """
        body_text = ""
        body_html = ""
        inline_images = []
        
        try:
            # For imap_tools messages, use the available attributes directly
            if hasattr(parsed_msg, 'text') and parsed_msg.text:
                body_text = parsed_msg.text.strip()
                
            if hasattr(parsed_msg, 'html') and parsed_msg.html:
                body_html = parsed_msg.html.strip()
                
            # If we have both, prefer HTML for format detection
            if body_html and body_text:
                body_format = 'both'
            elif body_html:
                body_format = 'html'
            else:
                body_format = 'text'
                
        except Exception as e:
            print(f"Error in MIME parts parsing: {e}")
            # Fallback to basic extraction
            if hasattr(parsed_msg, 'text') and parsed_msg.text:
                body_text = parsed_msg.text.strip()
            if hasattr(parsed_msg, 'html') and parsed_msg.html:
                body_html = parsed_msg.html.strip()
            body_format = 'text' if body_text else 'html' if body_html else 'text'
        
        return body_text, body_html, body_format, inline_images

    def _fallback_content_extraction(self, msg) -> Tuple[str, str, str]:
        """
        Fallback content extraction when MIME parsing fails
        
        Args:
            msg: Email message object
            
        Returns:
            Tuple of (body_text, body_html, body_format)
        """
        body_text = ""
        body_html = ""
        body_format = 'text'
        
        try:
            # Initialize variables
            raw_text = ""
            raw_html = ""
            
            # Try to get text version
            if hasattr(msg, 'text') and msg.text:
                raw_text = msg.text.strip()
                
            # Try to get HTML version
            if hasattr(msg, 'html') and msg.html:
                raw_html = msg.html.strip()
            
            # Enhanced HTML detection
            def is_html_content(content):
                if not content:
                    return False
                content_lower = content.lower()
                html_indicators = ['<html>', '<body>', '<div>', '<p>', '<br>', '<table>', '<img', '<a ', '<!doctype']
                html_tag_count = sum(1 for indicator in html_indicators if indicator in content_lower)
                general_tag_count = len([m for m in re.findall(r'<[^>]+>', content)])
                return html_tag_count >= 2 or general_tag_count >= 5
            
            # Smart content classification
            if raw_html:
                body_html = raw_html
                if raw_text and not is_html_content(raw_text):
                    body_text = raw_text
                    body_format = 'both'
                else:
                    body_format = 'html'
                    
            elif raw_text:
                if is_html_content(raw_text):
                    body_html = raw_text
                    body_format = 'html'
                else:
                    body_text = raw_text
                    body_format = 'text'
                    
        except Exception as e:
            print(f"Fallback content extraction failed: {e}")
        
        return body_text, body_html, body_format

    def _apply_auto_tags_safe(self, email_id: int, sender: str, subject: str, body: str,
                             attachments: list, user_id: int):
        """
        Apply auto-tag rules with improved error handling
        
        Args:
            email_id: Email ID
            sender: Email sender
            subject: Email subject
            body: Email body
            attachments: Email attachments
            user_id: User ID
        """
        try:
            rules = AutoTagRule.get_active_rules(user_id)
            applied_count = 0
            
            for rule in rules:
                if self.should_stop:
                    break
                    
                try:
                    if rule.check_match(sender, subject, body):
                        # Add tag to email
                        if rule.apply_to_email(email_id):
                            applied_count += 1
                            
                            # Save attachments if configured
                            if rule.save_attachments and rule.attachment_path and attachments:
                                self.attachment_service.save_attachments_safe(
                                    attachments, rule.attachment_path, email_id
                                )
                            
                except Exception as rule_error:
                    print(f"Error processing rule {rule.id}: {rule_error}")
                    continue
                    
        except Exception as e:
            print(f"Error in apply_auto_tags_safe: {e}")

    def _get_config(self, key: str, default: Any) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value
            
        Returns:
            Configuration value
        """
        # This would typically load from a config file
        # For now, return default values
        config_defaults = {
            'max_emails_per_fetch': 100,
            'auto_fetch_interval': 300,
            'session_days': 90,
            'redownload_attachments': False
        }
        
        return config_defaults.get(key, default)

    def stop_fetch(self):
        """Stop the email fetch operation"""
        self.should_stop = True

    def test_connection(self, imap_host: str, imap_port: int, email: str, password: str) -> Dict[str, Any]:
        """
        Test IMAP connection
        
        Args:
            imap_host: IMAP server host
            imap_port: IMAP server port
            email: Email address
            password: Email password
            
        Returns:
            Dict with test results: {'success': bool, 'error': str}
        """
        try:
            with MailBox(imap_host, port=imap_port).login(email, password, 'INBOX') as mailbox:
                # Try to get a small number of emails to verify connection
                messages = list(mailbox.fetch(limit=1))
                return {'success': True, 'error': None}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_email_count(self, imap_host: str, imap_port: int, email: str, password: str) -> Dict[str, Any]:
        """
        Get email count from server
        
        Args:
            imap_host: IMAP server host
            imap_port: IMAP server port
            email: Email address
            password: Email password
            
        Returns:
            Dict with count: {'success': bool, 'count': int, 'error': str}
        """
        try:
            with MailBox(imap_host, port=imap_port).login(email, password, 'INBOX') as mailbox:
                count = len(list(mailbox.fetch()))
                return {'success': True, 'count': count, 'error': None}
        except Exception as e:
            return {'success': False, 'count': 0, 'error': str(e)} 