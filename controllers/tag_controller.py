from typing import List, Optional, Dict, Any
from models.tag import Tag
from models.email import Email

class TagController:
    """Tag management business logic controller"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_user_tags(self, account_id: int = None) -> List[Tag]:
        """Get all tags for the current user with usage counts"""
        return Tag.get_user_tags(self.user_id, account_id)

    def create_tag(self, name: str, color: str = '#2196F3') -> Optional[Tag]:
        """Create a new tag"""
        if not name or not name.strip():
            return None
            
        return Tag.create_tag(name.strip(), self.user_id, color)

    def get_or_create_tag(self, name: str, color: str = '#2196F3') -> Tag:
        """Get existing tag or create new one"""
        if not name or not name.strip():
            raise ValueError("Tag name cannot be empty")
            
        return Tag.get_or_create_tag(name.strip(), self.user_id, color)

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """Get tag by name for the current user"""
        return Tag.get_by_name(name, self.user_id)

    def get_tag_by_id(self, tag_id: int) -> Optional[Tag]:
        """Get tag by ID"""
        tag = Tag.get_by_id(tag_id)
        if tag and tag.dashboard_user_id == self.user_id:
            return tag
        return None

    def update_tag_color(self, tag_id: int, color: str) -> bool:
        """Update tag color"""
        tag = self.get_tag_by_id(tag_id)
        if tag:
            tag.update_color(color)
            return True
        return False

    def delete_tag(self, tag_id: int) -> bool:
        """Delete a tag (will remove from all emails)"""
        tag = self.get_tag_by_id(tag_id)
        if tag:
            tag.delete()
            return True
        return False

    def add_tag_to_email(self, tag_name: str, email_id: int) -> bool:
        """Add a tag to an email"""
        # Get or create tag
        tag = self.get_or_create_tag(tag_name)
        if tag:
            return tag.add_to_email(email_id)
        return False

    def remove_tag_from_email(self, tag_name: str, email_id: int) -> bool:
        """Remove a tag from an email"""
        tag = self.get_tag_by_name(tag_name)
        if tag:
            return tag.remove_from_email(email_id)
        return False

    def get_emails_with_tag(self, tag_name: str, account_id: int) -> List[Email]:
        """Get all emails that have a specific tag"""
        tag = self.get_tag_by_name(tag_name)
        if not tag:
            return []
            
        return Email.get_emails_by_tag(account_id, tag_name)

    def get_tag_statistics(self, account_id: int = None) -> Dict[str, Any]:
        """Get statistics about tag usage"""
        tags = self.get_user_tags(account_id)
        
        total_tags = len(tags)
        total_usage = sum(getattr(tag, 'usage_count', 0) for tag in tags)
        most_used = max(tags, key=lambda t: getattr(t, 'usage_count', 0)) if tags else None
        
        return {
            'total_tags': total_tags,
            'total_usage': total_usage,
            'most_used_tag': most_used.name if most_used else None,
            'most_used_count': getattr(most_used, 'usage_count', 0) if most_used else 0
        }

    def clear_all_tags_from_account(self, account_id: int) -> int:
        """
        Remove all tags from all emails for an account
        
        Returns:
            Number of tag associations removed
        """
        import mysql.connector
        from config.database import DB_CONFIG
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # Remove all email-tag associations for emails in the account
            cursor.execute("""
                DELETE et FROM email_tags et
                INNER JOIN emails e ON et.email_id = e.id
                WHERE e.account_id = %s
            """, (account_id,))
            
            removed_count = cursor.rowcount
            conn.commit()
            return removed_count
            
        finally:
            cursor.close()
            conn.close()

    def get_tags_for_email(self, email_id: int) -> List[Tag]:
        """Get all tags associated with an email"""
        import mysql.connector
        from config.database import DB_CONFIG
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT t.* FROM tags t
                INNER JOIN email_tags et ON t.id = et.tag_id
                WHERE et.email_id = %s AND t.dashboard_user_id = %s
                ORDER BY t.name
            """, (email_id, self.user_id))
            
            tags = []
            for row in cursor.fetchall():
                tag = Tag(
                    id=row['id'],
                    name=row['name'],
                    color=row['color'],
                    dashboard_user_id=row['dashboard_user_id'],
                    created_at=row['created_at']
                )
                tags.append(tag)
            
            return tags
            
        finally:
            cursor.close()
            conn.close()

    def bulk_add_tag(self, tag_name: str, email_ids: List[int]) -> Dict[str, Any]:
        """
        Add a tag to multiple emails
        
        Args:
            tag_name: Name of the tag to add
            email_ids: List of email IDs to tag
            
        Returns:
            Dict with results: {'success': bool, 'processed': int, 'errors': List[str]}
        """
        tag = self.get_or_create_tag(tag_name)
        if not tag:
            return {'success': False, 'processed': 0, 'errors': ['Failed to create tag']}
        
        processed = 0
        errors = []
        
        for email_id in email_ids:
            try:
                if tag.add_to_email(email_id):
                    processed += 1
            except Exception as e:
                errors.append(f"Error adding tag to email {email_id}: {str(e)}")
        
        return {
            'success': True,
            'processed': processed,
            'errors': errors
        }

    def bulk_remove_tag(self, tag_name: str, email_ids: List[int]) -> Dict[str, Any]:
        """
        Remove a tag from multiple emails
        
        Args:
            tag_name: Name of the tag to remove
            email_ids: List of email IDs to untag
            
        Returns:
            Dict with results: {'success': bool, 'processed': int, 'errors': List[str]}
        """
        tag = self.get_tag_by_name(tag_name)
        if not tag:
            return {'success': False, 'processed': 0, 'errors': ['Tag not found']}
        
        processed = 0
        errors = []
        
        for email_id in email_ids:
            try:
                if tag.remove_from_email(email_id):
                    processed += 1
            except Exception as e:
                errors.append(f"Error removing tag from email {email_id}: {str(e)}")
        
        return {
            'success': True,
            'processed': processed,
            'errors': errors
        }

    def get_tag_suggestions(self, partial_name: str, limit: int = 10) -> List[str]:
        """
        Get tag name suggestions based on partial input
        
        Args:
            partial_name: Partial tag name to search for
            limit: Maximum number of suggestions to return
            
        Returns:
            List of suggested tag names
        """
        tags = self.get_user_tags()
        suggestions = []
        
        partial_lower = partial_name.lower()
        for tag in tags:
            if partial_lower in tag.name.lower():
                suggestions.append(tag.name)
                if len(suggestions) >= limit:
                    break
        
        return suggestions 