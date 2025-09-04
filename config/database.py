import mysql.connector
import os

# Try to load environment variables, fallback gracefully if dotenv not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using system environment variables only.")

# Database configuration from environment variables with fallbacks
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'email_manager')
}


def create_unified_database():
    """Create unified database with all necessary tables"""
    # Create connection config without database for initial connection
    tmp_config = {
        'host': DB_CONFIG['host'],
        'user': DB_CONFIG['user'],
        'password': DB_CONFIG['password']
    }
    
    # Add port if specified
    if 'port' in DB_CONFIG:
        tmp_config['port'] = DB_CONFIG['port']
    
    tmp = mysql.connector.connect(**tmp_config)
    cur = tmp.cursor()
    # Validate database name to prevent SQL injection
    db_name = DB_CONFIG['database']
    if not db_name.replace('_', '').replace('-', '').isalnum():
        raise ValueError(f"Invalid database name: {db_name}")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    cur.close()
    tmp.close()

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Dashboard users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            failed_attempts INT DEFAULT 0,
            locked_until TIMESTAMP NULL,
            reset_token VARCHAR(10) NULL,
            reset_token_expiry TIMESTAMP NULL,
            verification_code VARCHAR(6) NULL,
            verification_expiry TIMESTAMP NULL,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL
        )
    """)

    # Email accounts table (linked to dashboard users)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            dashboard_user_id INT NOT NULL,
            imap_host VARCHAR(255),
            imap_port INT DEFAULT 993,
            email VARCHAR(255),
            encrypted_password BLOB,
            last_sync TIMESTAMP NULL,
            sync_enabled BOOLEAN DEFAULT TRUE,
            session_expires TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_email (dashboard_user_id, email)
        )
    """)
    
    # Add imap_port column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE accounts ADD COLUMN imap_port INT DEFAULT 993 AFTER imap_host")
        print("Added imap_port column to accounts table")
    except mysql.connector.Error as e:
        if "Duplicate column name" in str(e):
            print("imap_port column already exists")
        else:
            print(f"Error adding imap_port column: {e}")

    # Emails table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uid VARCHAR(255),
            subject TEXT,
            sender TEXT,
            recipients TEXT,
            date DATETIME,
            has_attachment BOOLEAN DEFAULT FALSE,
            body LONGTEXT,
            body_text LONGTEXT,
            body_html LONGTEXT,
            body_format ENUM('text', 'html', 'both') DEFAULT 'text',
            size_bytes INT DEFAULT 0,
            read_status BOOLEAN DEFAULT FALSE,
            priority ENUM('high','normal','low') DEFAULT 'normal',
            account_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            UNIQUE KEY(uid, account_id),
            INDEX idx_date (date),
            INDEX idx_sender (sender(100)),
            INDEX idx_subject (subject(100)),
            INDEX idx_body_format (body_format)
        )
    """)

    # Tags table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            color VARCHAR(7) DEFAULT '#2196F3',
            dashboard_user_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_tag (dashboard_user_id, name)
        )
    """)

    # Email tags junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_tags (
            email_id INT,
            tag_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(email_id, tag_id),
            FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)

    # Auto tag rules with attachment saving
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auto_tag_rules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            rule_type ENUM('sender','subject','body','domain') NOT NULL,
            operator ENUM('contains','equals','starts_with','ends_with','regex') DEFAULT 'contains',
            value TEXT NOT NULL,
            tag_id INT NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            priority INT DEFAULT 0,
            save_attachments BOOLEAN DEFAULT FALSE,
            attachment_path TEXT NULL,
            dashboard_user_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
            FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
        )
    """)

    # Search history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            query TEXT NOT NULL,
            search_type VARCHAR(50),
            dashboard_user_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dashboard_user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
        )
    """)

    # Attachments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email_id INT NOT NULL,
            filename VARCHAR(255) NOT NULL,
            file_path TEXT NOT NULL,
            file_size INT DEFAULT 0,
            mime_type VARCHAR(100),
            content_type VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
            INDEX idx_email_id (email_id),
            INDEX idx_filename (filename(100)),
            INDEX idx_mime_type (mime_type)
        )
    """)

    # Device attachments table (for tracking files saved to device)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_attachments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            attachment_id INT NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            device_filename VARCHAR(255) NOT NULL,
            device_path TEXT NOT NULL,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (attachment_id) REFERENCES attachments(id) ON DELETE CASCADE,
            INDEX idx_attachment_id (attachment_id),
            INDEX idx_original_filename (original_filename(100)),
            INDEX idx_device_filename (device_filename(100))
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

# Initialize database
create_unified_database()