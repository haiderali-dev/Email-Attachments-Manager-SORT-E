import os
import re
import mysql.connector
from datetime import datetime, timedelta
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from imap_tools import MailBox
from config.database import DB_CONFIG
from config.settings import CONFIG
from services.encryption_service import decrypt_text

class EmailFetchWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)
    emails_processed = pyqtSignal(int, int)  # current_count, total_count
    batch_complete = pyqtSignal(list)  # list of processed emails for UI update

    def __init__(self, account_info, user_id, start_date=None):
        super().__init__()
        self.account_info = account_info
        self.user_id = user_id
        self.start_date = start_date
        self.should_stop = False
        self.batch_size = CONFIG.get('progressive_batch_size', 100)
        self.commit_interval = CONFIG.get('progressive_commit_interval', 50)

    def stop(self):
        """Stop the worker thread"""
        self.should_stop = True

    def run(self):
        conn = None
        cursor = None
        
        try:
            imap_host, imap_port, email, encrypted_password = self.account_info
            password = decrypt_text(encrypted_password)
            
            self.progress.emit("Connecting to email server...")
            
            # Connect to database first
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Get account ID
            cursor.execute("SELECT id FROM accounts WHERE email=%s AND dashboard_user_id=%s", 
                         (email, self.user_id))
            account_result = cursor.fetchone()
            if not account_result:
                self.error.emit("Account not found in database")
                return
            account_id = account_result[0]
            
            with MailBox(imap_host, port=imap_port).login(email, password, 'INBOX') as mailbox:
                if self.should_stop:
                    return
                    
                self.progress.emit("Fetching email list...")
                
                # Get ALL emails from the specified time period (no limit)
                if self.start_date:
                    self.progress.emit(f"Fetching ALL emails from {self.start_date} onwards...")
                    date_filter = self.start_date.strftime("%d-%b-%Y")
                    messages = list(mailbox.fetch(f'SINCE {date_filter}', reverse=True))
                else:
                    self.progress.emit("Fetching ALL emails...")
                    messages = list(mailbox.fetch(reverse=True))
                
                if not messages:
                    self.progress.emit("No emails found")
                    self.finished.emit(0)
                    return
                
                total_messages = len(messages)
                self.progress.emit(f"Found {total_messages} emails to process")
                
                # Emit initial progress update
                self.emails_processed.emit(0, total_messages)
                
                new_count = 0
                processed_emails = []
                
                # Process emails in batches for UI responsiveness
                for i, msg in enumerate(messages):
                    if self.should_stop:
                        break
                        
                    try:
                        self.progress.emit(f"Processing email {i+1}/{total_messages}")
                        
                        # Process the email
                        email_result = self._process_single_email(msg, account_id, cursor, conn)
                        if email_result:
                            new_count += 1
                            processed_emails.append(email_result)
                        
                        # Update progress immediately for each email
                        self.emails_processed.emit(i + 1, total_messages)
                        
                        # Small delay to make UI responsive and show progressive loading
                        if i % 5 == 0:  # Every 5 emails
                            QThread.msleep(10)  # 10ms delay
                        
                        # Send batch updates to UI when batch size is reached
                        if len(processed_emails) >= self.batch_size:
                            self.batch_complete.emit(processed_emails.copy())
                            processed_emails.clear()
                        
                        # Commit to database periodically
                        if (i + 1) % self.commit_interval == 0:
                            conn.commit()
                            self.progress.emit(f"Committed {i + 1} emails to database")
                            
                    except Exception as msg_error:
                        print(f"Error processing email {i+1}: {msg_error}")
                        continue
                
                if not self.should_stop:
                    # Send any remaining emails in the batch
                    if processed_emails:
                        self.batch_complete.emit(processed_emails)
                    
                    # Final commit
                    conn.commit()
                    
                    # Update last sync
                    try:
                        cursor.execute("UPDATE accounts SET last_sync=NOW() WHERE id=%s", (account_id,))
                        conn.commit()
                    except Exception as sync_error:
                        print(f"Error updating sync time: {sync_error}")
                    
                    self.progress.emit(f"Fetch completed! Processed {new_count} new emails out of {total_messages} total")
                    self.finished.emit(new_count)
                else:
                    self.progress.emit("Operation cancelled by user")
                    self.finished.emit(new_count)
                
        except mysql.connector.Error as db_error:
            self.error.emit(f"Database error: {str(db_error)}")
        except Exception as e:
            self.error.emit(f"Fetch error: {str(e)}")
        finally:
            # Clean up database connection
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def _process_single_email(self, msg, account_id, cursor, conn):
        """
        Process a single email message with improved error handling
        
        Args:
            msg: Email message object
            account_id: Database account ID
            cursor: Database cursor
            conn: Database connection
            
        Returns:
            Email data dict if successful, None otherwise
        """
        try:
            uid = str(msg.uid) if msg.uid else f"no_uid_{id(msg)}"
            subject = msg.subject or "(No subject)"
            sender = str(msg.from_) if msg.from_ else "(Unknown sender)"
            recipients = ", ".join([str(addr) for addr in msg.to]) if msg.to else ""
            date = msg.date
            
            # Enhanced MIME parsing for email body
            body = ""
            body_text = ""
            body_html = ""
            body_format = "text"
            
            try:
                # Use enhanced MIME parsing from email service
                from services.email_service import EmailService
                email_service = EmailService()
                
                # Parse the email content using the correct MIME parsing method
                body_text, body_html, body_format, inline_images = email_service._parse_mime_content(msg)
                
                # Set body to the best available content for backward compatibility
                if body_html and body_format == 'html':
                    body = body_html
                elif body_text:
                    body = body_text
                else:
                    body = msg.text or msg.html or ""
                    
            except Exception as body_error:
                print(f"Error with enhanced MIME parsing, using fallback: {body_error}")
                # Fallback to simple body extraction
                try:
                    body = msg.text or msg.html or ""
                    if body:
                        if '<html' in body.lower() or '<!DOCTYPE' in body.lower():
                            body_html = body
                            body_text = ""
                            body_format = "html"
                        else:
                            body_text = body
                            body_html = ""
                            body_format = "text"
                except Exception as fallback_error:
                    print(f"Fallback body extraction failed: {fallback_error}")
                    body = "(Error reading email content)"
                    body_text = ""
                    body_html = ""
                    body_format = "text"
            
            size_bytes = len(body.encode('utf-8')) if body else 0
            has_attachment = bool(msg.attachments) if hasattr(msg, 'attachments') else False
            
            # Check if email already exists
            cursor.execute("SELECT id FROM emails WHERE uid=%s AND account_id=%s", (uid, account_id))
            existing_email = cursor.fetchone()
            
            if existing_email:
                # Email exists - only apply auto-tags if needed
                existing_email_id = existing_email[0]
                print(f"Email {uid} already exists (ID: {existing_email_id}), checking for new tags...")
                
                # Apply auto-tags but with smart attachment handling
                self.apply_auto_tags_safe(cursor, conn, existing_email_id, sender, subject, body, 
                                        msg.attachments if hasattr(msg, 'attachments') else [])
                return None  # Not a new email
            
            # Insert new email with duplicate key handling
            try:
                cursor.execute("""
                    INSERT INTO emails (uid, subject, sender, recipients, date, has_attachment, 
                                      body, body_text, body_html, body_format, size_bytes, account_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        subject = VALUES(subject),
                        sender = VALUES(sender),
                        recipients = VALUES(recipients),
                        date = VALUES(date),
                        has_attachment = VALUES(has_attachment),
                        body = VALUES(body),
                        body_text = VALUES(body_text),
                        body_html = VALUES(body_html),
                        body_format = VALUES(body_format),
                        size_bytes = VALUES(size_bytes),
                        updated_at = CURRENT_TIMESTAMP
                """, (uid, subject, sender, recipients, date, has_attachment, body, body_text, body_html, body_format, size_bytes, account_id))
                
                # Check if this was an insert or update
                if cursor.lastrowid > 0:
                    # This was a new email
                    email_id = cursor.lastrowid
                    print(f"Inserted new email {uid} (ID: {email_id})")
                    
                    # Apply auto-tag rules to new email (will download attachments if configured)
                    self.apply_auto_tags_safe(cursor, conn, email_id, sender, subject, body, 
                                            msg.attachments if hasattr(msg, 'attachments') else [])
                    
                    # Return email data for UI update
                    return {
                        'id': email_id,
                        'uid': uid,
                        'subject': subject,
                        'sender': sender,
                        'recipients': recipients,
                        'date': date,
                        'has_attachment': has_attachment,
                        'body': body,
                        'body_text': body_text,
                        'body_html': body_html,
                        'body_format': body_format,
                        'size_bytes': size_bytes,
                        'account_id': account_id
                    }
                else:
                    # This was an update of existing email
                    print(f"Updated existing email {uid}")
                    
                    # Get the existing email ID for tag updates
                    cursor.execute("SELECT id FROM emails WHERE uid=%s AND account_id=%s", (uid, account_id))
                    existing_email_id = cursor.fetchone()[0]
                    
                    # Apply auto-tags to existing email
                    self.apply_auto_tags_safe(cursor, conn, existing_email_id, sender, subject, body, 
                                            msg.attachments if hasattr(msg, 'attachments') else [])
                    return None  # Not a new email
                
            except mysql.connector.Error as db_error:
                print(f"Database error inserting email: {db_error}")
                conn.rollback()
                return None
                
        except Exception as msg_error:
            print(f"Error processing email: {msg_error}")
            return None

    def apply_auto_tags_safe(self, cursor, conn, email_id, sender, subject, body, attachments):
        """
        Apply auto-tag rules with improved error handling
        
        Args:
            cursor: Database cursor
            conn: Database connection
            email_id: Email ID
            sender: Email sender
            subject: Email subject
            body: Email body
            attachments: Email attachments
        """
        try:
            # Get active auto-tag rules for this user
            cursor.execute("""
                SELECT r.*, t.name as tag_name 
                FROM auto_tag_rules r 
                JOIN tags t ON r.tag_id = t.id 
                WHERE r.dashboard_user_id = %s AND r.enabled = TRUE 
                ORDER BY r.priority DESC
            """, (self.user_id,))
            
            rules = cursor.fetchall()
            applied_count = 0
            
            # Initialize rule_id to avoid scope issues
            rule_id = None
            
            for rule in rules:
                if self.should_stop:
                    break
                    
                try:
                    rule_id, rule_type, operator, value, tag_id, enabled, priority, save_attachments, attachment_path, dashboard_user_id, created_at, updated_at, tag_name = rule
                    
                    # Check if rule matches
                    if self._rule_matches(rule_type, operator, value, sender, subject, body):
                        # Add tag to email
                        cursor.execute("""
                            INSERT IGNORE INTO email_tags (email_id, tag_id) 
                            VALUES (%s, %s)
                        """, (email_id, tag_id))
                        
                        applied_count += 1
                        print(f"Applied tag '{tag_name}' to email {email_id}")
                        
                        # Save attachments if configured
                        if save_attachments and attachment_path and attachments:
                            self._save_attachments_safe(cursor, conn, email_id, attachments, attachment_path)
                            
                except Exception as rule_error:
                    # Use rule_id if available, otherwise use a placeholder
                    rule_identifier = rule_id if rule_id is not None else 'unknown'
                    print(f"Error processing rule {rule_identifier}: {rule_error}")
                    continue
                    
            if applied_count > 0:
                print(f"Applied {applied_count} tags to email {email_id}")
                
        except Exception as e:
            print(f"Error in apply_auto_tags_safe: {e}")

    def _rule_matches(self, rule_type, operator, value, sender, subject, body):
        """
        Check if a rule matches the email content
        
        Args:
            rule_type: Type of rule (sender, subject, body, domain)
            operator: Comparison operator
            value: Rule value to match against
            sender: Email sender
            subject: Email subject
            body: Email body
            
        Returns:
            True if rule matches, False otherwise
        """
        try:
            if rule_type == 'sender':
                content = sender
            elif rule_type == 'subject':
                content = subject
            elif rule_type == 'body':
                content = body
            elif rule_type == 'domain':
                # Extract domain from sender
                if '@' in sender:
                    content = sender.split('@')[1]
                else:
                    content = sender
            else:
                return False
            
            if not content:
                return False
            
            content = content.lower()
            value = value.lower()
            
            if operator == 'contains':
                return value in content
            elif operator == 'equals':
                return content == value
            elif operator == 'starts_with':
                return content.startswith(value)
            elif operator == 'ends_with':
                return content.endswith(value)
            elif operator == 'regex':
                try:
                    import re
                    return re.search(value, content, re.IGNORECASE) is not None
                except:
                    return False
            else:
                return False
                
        except Exception as e:
            print(f"Error in rule matching: {e}")
            return False

    def _save_attachments_safe(self, cursor, conn, email_id, attachments, base_path):
        """
        Save email attachments safely
        
        Args:
            cursor: Database cursor
            conn: Database connection
            email_id: Email ID
            attachments: List of attachments
            base_path: Base path for saving attachments
        """
        try:
            if not attachments or not base_path:
                return
            
            # Create directory if it doesn't exist
            os.makedirs(base_path, exist_ok=True)
            
            for attachment in attachments:
                if self.should_stop:
                    break
                    
                try:
                    filename = getattr(attachment, 'filename', f'attachment_{id(attachment)}')
                    filepath = os.path.join(base_path, filename)
                    
                    # Write attachment data
                    with open(filepath, 'wb') as f:
                        if hasattr(attachment, 'payload'):
                            f.write(attachment.payload)
                        elif hasattr(attachment, 'content'):
                            f.write(attachment.content)
                    
                    # Get file size
                    file_size = os.path.getsize(filepath)
                    
                    # Save to database
                    cursor.execute("""
                        INSERT INTO attachments (email_id, filename, file_path, file_size, mime_type, content_type)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (email_id, filename, filepath, file_size, 
                          getattr(attachment, 'mime_type', 'unknown'),
                          getattr(attachment, 'content_type', 'unknown')))
                    
                    print(f"Saved attachment: {filename}")
                    
                except Exception as att_error:
                    print(f"Error saving attachment {filename}: {att_error}")
                    continue
                    
        except Exception as e:
            print(f"Error in _save_attachments_safe: {e}")

    def fetch_new_emails_since(self, since_timestamp):
        """Fetch only new emails since a specific timestamp"""
        conn = None
        cursor = None
        
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            imap_host, imap_port, email, encrypted_password = self.account_info
            password = decrypt_text(encrypted_password)
            
            # Get account_id from database
            cursor.execute("SELECT id FROM accounts WHERE email=%s AND dashboard_user_id=%s", 
                         (email, self.user_id))
            result = cursor.fetchone()
            if not result:
                return 0
            account_id = result[0]
            
            with MailBox(imap_host, port=imap_port).login(email, password, 'INBOX') as mailbox:
                if self.should_stop:
                    return 0
                    
                # Use SINCE filter with timestamp for new emails only
                date_filter = since_timestamp.strftime("%d-%b-%Y")
                messages = list(mailbox.fetch(f'SINCE {date_filter}', reverse=True))
                
                if not messages:
                    return 0
                
                new_count = 0
                total_messages = len(messages)
                
                for i, msg in enumerate(messages):
                    if self.should_stop:
                        break
                        
                    try:
                        # Process email (simplified for real-time monitoring)
                        uid = str(msg.uid) if msg.uid else f"no_uid_{i}"
                        
                        # Check if email already exists
                        cursor.execute("SELECT id FROM emails WHERE uid=%s AND account_id=%s", (uid, account_id))
                        if cursor.fetchone():
                            continue  # Email already exists
                        
                        # Process new email
                        email_result = self._process_single_email(msg, account_id, cursor, conn)
                        if email_result:
                            new_count += 1
                        
                        # Commit periodically
                        if (i + 1) % self.commit_interval == 0:
                            conn.commit()
                            
                    except Exception as msg_error:
                        print(f"Error processing new email {i+1}: {msg_error}")
                        continue
                
                # Final commit
                conn.commit()
                return new_count
                
        except Exception as e:
            print(f"Error in fetch_new_emails_since: {e}")
            return 0
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass


class RealTimeEmailMonitor(QThread):
    """Real-time email monitoring thread"""
    new_emails = pyqtSignal(int)  # Number of new emails
    error = pyqtSignal(str)  # Error message
    
    def __init__(self, account_info, user_id):
        super().__init__()
        self.account_info = account_info
        self.user_id = user_id
        self.should_stop = False
        self.monitoring_interval = CONFIG.get('monitoring_interval', 30)
        self.last_check = None
        
    def stop(self):
        """Stop the monitoring thread"""
        self.should_stop = True
        
    def run(self):
        """Run the monitoring loop"""
        while not self.should_stop:
            try:
                # Get current time for monitoring
                now = datetime.now()
                
                # Check for new emails
                if self.last_check is None:
                    # First run - check for emails since 1 hour ago
                    since_time = now - timedelta(hours=1)
                else:
                    since_time = self.last_check
                
                # Fetch new emails
                worker = EmailFetchWorker(self.account_info, self.user_id)
                new_count = worker.fetch_new_emails_since(since_time)
                
                if new_count > 0:
                    self.new_emails.emit(new_count)
                
                # Update last check time
                self.last_check = now
                
                # Sleep for monitoring interval
                for _ in range(self.monitoring_interval):
                    if self.should_stop:
                        break
                    self.msleep(1000)  # Sleep in 1-second intervals
                    
            except Exception as e:
                self.error.emit(f"Monitoring error: {str(e)}")
                # Wait before retrying
                for _ in range(60):  # Wait 1 minute before retry
                    if self.should_stop:
                        break
                    self.msleep(1000)