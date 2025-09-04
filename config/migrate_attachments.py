import os
import mimetypes
import mysql.connector
from config.database import DB_CONFIG
from models.attachment import Attachment

def migrate_existing_attachments():
    """Migrate existing attachments from file system to database"""
    print("Starting attachment migration...")
    
    # Create attachments table if it doesn't exist
    Attachment.create_database()
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Get all emails with attachments
        cursor.execute("""
            SELECT id, account_id FROM emails WHERE has_attachment = TRUE
        """)
        
        emails_with_attachments = cursor.fetchall()
        print(f"Found {len(emails_with_attachments)} emails with attachments")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for email_id, account_id in emails_with_attachments:
            email_folder = os.path.join('attachments', f'email_{email_id}')
            
            if not os.path.exists(email_folder):
                print(f"Email folder not found: {email_folder}")
                continue
            
            # Get all files in the email folder
            try:
                files = [f for f in os.listdir(email_folder) 
                        if os.path.isfile(os.path.join(email_folder, f))]
                
                for filename in files:
                    file_path = os.path.join(email_folder, filename)
                    
                    # Check if already in database
                    cursor.execute("""
                        SELECT id FROM attachments 
                        WHERE email_id = %s AND filename = %s
                    """, (email_id, filename))
                    
                    if cursor.fetchone():
                        print(f"Attachment already exists in DB: {filename}")
                        skipped_count += 1
                        continue
                    
                    # Get file info
                    try:
                        file_size = os.path.getsize(file_path)
                        mime_type, _ = mimetypes.guess_type(filename)
                        
                        # Create attachment record
                        attachment = Attachment.create_attachment(
                            email_id=email_id,
                            filename=filename,
                            file_path=file_path,
                            file_size=file_size,
                            mime_type=mime_type,
                            content_type=mime_type
                        )
                        
                        if attachment:
                            migrated_count += 1
                            print(f"Migrated: {filename} ({format_size(file_size)})")
                        else:
                            error_count += 1
                            print(f"Failed to create DB record for: {filename}")
                    
                    except Exception as e:
                        error_count += 1
                        print(f"Error processing {filename}: {e}")
            
            except Exception as e:
                print(f"Error processing email {email_id}: {e}")
                error_count += 1
        
        print(f"\nMigration completed:")
        print(f"  Migrated: {migrated_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Errors: {error_count}")
        
    finally:
        cursor.close()
        conn.close()

def format_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

if __name__ == "__main__":
    migrate_existing_attachments() 