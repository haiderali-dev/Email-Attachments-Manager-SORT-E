from typing import List, Optional, Dict, Any, Tuple
from models.rule import AutoTagRule
from models.tag import Tag
from models.email import Email
from services.attachment_service import AttachmentService

class RuleController:
    """Auto-tag rule business logic controller"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.attachment_service = AttachmentService()

    def get_user_rules(self) -> List[AutoTagRule]:
        """Get all auto-tag rules for the current user"""
        return AutoTagRule.get_user_rules(self.user_id)

    def get_active_rules(self) -> List[AutoTagRule]:
        """Get all active auto-tag rules for the current user"""
        return AutoTagRule.get_active_rules(self.user_id)

    def create_rule(self, rule_type: str, operator: str, value: str, tag_id: int,
                   save_attachments: bool = False, attachment_path: str = None,
                   priority: int = 0) -> Optional[AutoTagRule]:
        """Create a new auto-tag rule"""
        # Validate rule parameters
        if not rule_type or not operator or not value or not tag_id:
            return None
            
        # Validate tag belongs to user
        tag = Tag.get_by_id(tag_id)
        if not tag or tag.dashboard_user_id != self.user_id:
            return None
            
        return AutoTagRule.create_rule(
            rule_type, operator, value, tag_id, self.user_id,
            save_attachments, attachment_path, priority
        )

    def get_rule_by_id(self, rule_id: int) -> Optional[AutoTagRule]:
        """Get rule by ID"""
        rule = AutoTagRule.get_by_id(rule_id)
        if rule and rule.dashboard_user_id == self.user_id:
            return rule
        return None

    def update_rule(self, rule_id: int, **kwargs) -> bool:
        """Update rule fields"""
        rule = self.get_rule_by_id(rule_id)
        if rule:
            rule.update(**kwargs)
            return True
        return False

    def toggle_rule(self, rule_id: int) -> bool:
        """Toggle rule enabled status"""
        rule = self.get_rule_by_id(rule_id)
        if rule:
            rule.toggle_enabled()
            return True
        return False

    def delete_rule(self, rule_id: int) -> bool:
        """Delete a rule"""
        rule = self.get_rule_by_id(rule_id)
        if rule:
            rule.delete()
            return True
        return False

    def apply_rule_to_email(self, rule_id: int, email_id: int) -> bool:
        """Apply a specific rule to an email"""
        rule = self.get_rule_by_id(rule_id)
        if not rule:
            return False
            
        email = Email.get_by_id(email_id)
        if not email:
            return False
            
        # Verify email belongs to user
        from models.email_account import EmailAccount
        account = EmailAccount.get_by_id(email.account_id)
        if not account or account.dashboard_user_id != self.user_id:
            return False
            
        # Check if rule matches
        if rule.check_match(email.sender, email.subject, email.body):
            # Apply tag
            if rule.apply_to_email(email_id):
                # Save attachments if configured
                if rule.save_attachments and rule.attachment_path:
                    self.attachment_service.save_email_attachments(
                        email_id, rule.attachment_path
                    )
                return True
                
        return False

    def apply_all_rules_to_email(self, email_id: int) -> int:
        """
        Apply all active rules to an email
        
        Returns:
            Number of rules applied
        """
        email = Email.get_by_id(email_id)
        if not email:
            return 0
            
        # Verify email belongs to user
        from models.email_account import EmailAccount
        account = EmailAccount.get_by_id(email.account_id)
        if not account or account.dashboard_user_id != self.user_id:
            return 0
            
        rules = self.get_active_rules()
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



    def test_rule(self, rule_type: str, operator: str, value: str, 
                  test_sender: str, test_subject: str, test_body: str) -> bool:
        """
        Test if a rule would match given email data
        
        Args:
            rule_type: Type of rule (sender, subject, body, domain)
            operator: Rule operator (contains, equals, starts_with, ends_with, regex)
            value: Rule value to match against
            test_sender: Sender email to test
            test_subject: Subject to test
            test_body: Body to test
            
        Returns:
            True if rule would match, False otherwise
        """
        # Create temporary rule object for testing
        temp_rule = AutoTagRule(
            rule_type=rule_type,
            operator=operator,
            value=value
        )
        
        return temp_rule.check_match(test_sender, test_subject, test_body)

    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about auto-tag rules"""
        rules = self.get_user_rules()
        
        total_rules = len(rules)
        active_rules = len([r for r in rules if r.enabled])
        rules_with_attachments = len([r for r in rules if r.save_attachments])
        
        # Count rules by type
        rule_types = {}
        for rule in rules:
            rule_types[rule.rule_type] = rule_types.get(rule.rule_type, 0) + 1
        
        return {
            'total_rules': total_rules,
            'active_rules': active_rules,
            'rules_with_attachments': rules_with_attachments,
            'rule_types': rule_types
        }

    def validate_rule_parameters(self, rule_type: str, operator: str, value: str) -> Tuple[bool, str]:
        """
        Validate rule parameters
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not rule_type or rule_type not in ['sender', 'subject', 'body', 'domain']:
            return False, "Invalid rule type"
            
        if not operator or operator not in ['contains', 'equals', 'starts_with', 'ends_with', 'regex']:
            return False, "Invalid operator"
            
        if not value or not value.strip():
            return False, "Rule value cannot be empty"
            
        # Validate regex if operator is regex
        if operator == 'regex':
            try:
                import re
                re.compile(value)
            except re.error:
                return False, "Invalid regular expression"
        
        return True, ""

    def get_rule_preview(self, rule_type: str, operator: str, value: str, 
                        account_id: int, limit: int = 10) -> List[Email]:
        """
        Get preview of emails that would match a rule
        
        Args:
            rule_type: Type of rule
            operator: Rule operator
            value: Rule value
            account_id: Account to search in
            limit: Maximum number of emails to return
            
        Returns:
            List of emails that would match the rule
        """
        from models.email_account import EmailAccount
        
        account = EmailAccount.get_by_id(account_id)
        if not account or account.dashboard_user_id != self.user_id:
            return []
            
        emails = Email.get_account_emails(account_id, limit=limit)
        matching_emails = []
        
        # Create temporary rule for testing
        temp_rule = AutoTagRule(
            rule_type=rule_type,
            operator=operator,
            value=value
        )
        
        for email in emails:
            if temp_rule.check_match(email.sender, email.subject, email.body):
                matching_emails.append(email)
        
        return matching_emails 