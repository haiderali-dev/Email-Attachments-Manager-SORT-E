from typing import List, Optional, Dict, Any
from models.email import Email
from models.email_account import EmailAccount
from models.tag import Tag
from models.rule import AutoTagRule
from services.email_service import EmailService
from services.attachment_service import AttachmentService

class EmailController:
    """Email management business logic controller"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.email_service = EmailService()
        self.attachment_service = AttachmentService()

    def get_user_accounts(self) -> List[EmailAccount]:
        """Get all email accounts for the current user"""
        return EmailAccount.get_user_accounts(self.user_id)

    def create_email_account(self, imap_host: str, imap_port: int, email: str, password: str) -> Optional[EmailAccount]:
        """Create a new email account"""
        return EmailAccount.create_account(self.user_id, imap_host, imap_port, email, password)

    def delete_email_account(self, account_id: int) -> bool:
        """Delete an email account and all associated data"""
        account = EmailAccount.get_by_id(account_id)
        if account and account.dashboard_user_id == self.user_id:
            account.delete()
            return True
        return False

    def fetch_emails(self, account_id: int, progress_callback=None) -> Dict[str, Any]:
        """
        Fetch emails for an account
        
        Args:
            account_id: Email account ID
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with results: {'success': bool, 'new_count': int, 'error': str}
        """
        account = EmailAccount.get_by_id(account_id)
        if not account or account.dashboard_user_id != self.user_id:
            return {'success': False, 'new_count': 0, 'error': 'Account not found'}
            
        try:
            if progress_callback:
                progress_callback("Connecting to email server...")
                
            # Fetch emails using email service
            result = self.email_service.fetch_emails(
                account.imap_host, 
                account.imap_port,
                account.email, 
                account.get_password(),
                account_id,
                self.user_id,
                progress_callback
            )
            
            if result['success']:
                # Update last sync
                account.update_last_sync()
                
            return result
            
        except Exception as e:
            return {'success': False, 'new_count': 0, 'error': str(e)}

    def get_emails(self, account_id: int, search_text: str = None, 
                   status_filter: str = None, limit: int = None) -> List[Email]:
        """Get emails for an account with optional filtering"""
        account = EmailAccount.get_by_id(account_id)
        if not account or account.dashboard_user_id != self.user_id:
            return []
            
        return Email.get_account_emails(account_id, search_text, status_filter, limit)

    def get_emails_by_tag(self, account_id: int, tag_name: str) -> List[Email]:
        """Get emails with a specific tag"""
        account = EmailAccount.get_by_id(account_id)
        if not account or account.dashboard_user_id != self.user_id:
            return []
            
        return Email.get_emails_by_tag(account_id, tag_name)

    def get_email_by_id(self, email_id: int) -> Optional[Email]:
        """Get email by ID"""
        email = Email.get_by_id(email_id)
        if email:
            # Verify the email belongs to the user
            account = EmailAccount.get_by_id(email.account_id)
            if account and account.dashboard_user_id == self.user_id:
                return email
        return None

    def mark_email_as_read(self, email_id: int) -> bool:
        """Mark email as read"""
        email = self.get_email_by_id(email_id)
        if email:
            email.mark_as_read()
            return True
        return False

    def mark_email_as_unread(self, email_id: int) -> bool:
        """Mark email as unread"""
        email = self.get_email_by_id(email_id)
        if email:
            email.mark_as_unread()
            return True
        return False

    def delete_email(self, email_id: int) -> bool:
        """Delete an email"""
        email = self.get_email_by_id(email_id)
        if email:
            email.delete()
            return True
        return False

    def get_email_statistics(self, account_id: int) -> Dict[str, Any]:
        """Get email statistics for an account"""
        account = EmailAccount.get_by_id(account_id)
        if not account or account.dashboard_user_id != self.user_id:
            return {}
            
        emails = Email.get_account_emails(account_id)
        
        total_emails = len(emails)
        unread_emails = len([e for e in emails if not e.read_status])
        with_attachments = len([e for e in emails if e.has_attachment])
        
        # Calculate total size
        total_size = sum(e.size_bytes for e in emails)
        
        # Get emails from last 7 days
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        this_week = len([e for e in emails if e.date and e.date >= week_ago])
        
        return {
            'total_emails': total_emails,
            'unread_emails': unread_emails,
            'with_attachments': with_attachments,
            'total_size': total_size,
            'this_week': this_week
        }

    def apply_auto_tags_to_email(self, email_id: int) -> int:
        """
        Apply all active auto-tag rules to an email
        
        Returns:
            Number of tags applied
        """
        email = self.get_email_by_id(email_id)
        if not email:
            return 0
            
        rules = AutoTagRule.get_active_rules(self.user_id)
        applied_count = 0
        
        for rule in rules:
            if rule.check_match(email.sender, email.subject, email.body):
                if rule.apply_to_email(email_id):
                    applied_count += 1
                    
                    # Save attachments if configured
                    if rule.save_attachments and rule.attachment_path:
                        self.attachment_service.save_email_attachments(
                            email_id, rule.attachment_path
                        )
        
        return applied_count



    def search_emails(self, account_id: int, search_criteria: Dict[str, Any]) -> List[Email]:
        """
        Advanced email search
        
        Args:
            account_id: Email account ID
            search_criteria: Dict with search parameters
            
        Returns:
            List of matching emails
        """
        account = EmailAccount.get_by_id(account_id)
        if not account or account.dashboard_user_id != self.user_id:
            return []
            
        # This would implement advanced search logic
        # For now, return basic search results
        search_text = search_criteria.get('text', '')
        return Email.get_account_emails(account_id, search_text=search_text)

    def bulk_operations(self, account_id: int, operation: str, 
                       email_ids: List[int], **kwargs) -> Dict[str, Any]:
        """
        Perform bulk operations on emails
        
        Args:
            account_id: Email account ID
            operation: Operation type ('mark_read', 'mark_unread', 'delete', 'add_tag', 'remove_tag')
            email_ids: List of email IDs to operate on
            **kwargs: Additional parameters (e.g., tag_name for tag operations)
            
        Returns:
            Dict with results
        """
        account = EmailAccount.get_by_id(account_id)
        if not account or account.dashboard_user_id != self.user_id:
            return {'success': False, 'processed': 0, 'error': 'Account not found'}
            
        processed = 0
        errors = []
        
        for email_id in email_ids:
            try:
                if operation == 'mark_read':
                    if self.mark_email_as_read(email_id):
                        processed += 1
                elif operation == 'mark_unread':
                    if self.mark_email_as_unread(email_id):
                        processed += 1
                elif operation == 'delete':
                    if self.delete_email(email_id):
                        processed += 1
                elif operation == 'add_tag':
                    tag_name = kwargs.get('tag_name')
                    if tag_name:
                        tag = Tag.get_or_create_tag(tag_name, self.user_id)
                        if tag and tag.add_to_email(email_id):
                            processed += 1
                elif operation == 'remove_tag':
                    tag_name = kwargs.get('tag_name')
                    if tag_name:
                        tag = Tag.get_by_name(tag_name, self.user_id)
                        if tag and tag.remove_from_email(email_id):
                            processed += 1
            except Exception as e:
                errors.append(f"Error processing email {email_id}: {str(e)}")
        
        return {
            'success': True,
            'processed': processed,
            'errors': errors
        } 