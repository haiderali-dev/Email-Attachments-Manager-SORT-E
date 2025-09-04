"""
Database Migration Utility
Handles database schema updates for existing installations
"""

import mysql.connector
from config.database import DB_CONFIG

def migrate_database():
    """Run database migrations to update schema"""
    conn = None
    cursor = None
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔧 Running database migrations...")
        
        # Check if updated_at column exists in emails table
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'emails' 
            AND COLUMN_NAME = 'updated_at'
        """, (DB_CONFIG['database'],))
        
        if not cursor.fetchone():
            print("📝 Adding updated_at column to emails table...")
            cursor.execute("""
                ALTER TABLE emails 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            """)
            print("✅ updated_at column added successfully")
        else:
            print("✅ updated_at column already exists")
        
        # Check if updated_at column exists in accounts table
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'accounts' 
            AND COLUMN_NAME = 'updated_at'
        """, (DB_CONFIG['database'],))
        
        if not cursor.fetchone():
            print("📝 Adding updated_at column to accounts table...")
            cursor.execute("""
                ALTER TABLE accounts 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            """)
            print("✅ updated_at column added to accounts table")
        else:
            print("✅ updated_at column already exists in accounts table")
        
        # Check if updated_at column exists in dashboard_users table
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'dashboard_users' 
            AND COLUMN_NAME = 'updated_at'
        """, (DB_CONFIG['database'],))
        
        if not cursor.fetchone():
            print("📝 Adding updated_at column to dashboard_users table...")
            cursor.execute("""
                ALTER TABLE dashboard_users 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            """)
            print("✅ updated_at column added to dashboard_users table")
        else:
            print("✅ updated_at column already exists in dashboard_users table")
        
        # Check if updated_at column exists in tags table
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'tags' 
            AND COLUMN_NAME = 'updated_at'
        """, (DB_CONFIG['database'],))
        
        if not cursor.fetchone():
            print("📝 Adding updated_at column to tags table...")
            cursor.execute("""
                ALTER TABLE tags 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            """)
            print("✅ updated_at column added to tags table")
        else:
            print("✅ updated_at column already exists in tags table")
        
        # Check if updated_at column exists in auto_tag_rules table
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'auto_tag_rules' 
            AND COLUMN_NAME = 'updated_at'
        """, (DB_CONFIG['database'],))
        
        if not cursor.fetchone():
            print("📝 Adding updated_at column to auto_tag_rules table...")
            cursor.execute("""
                ALTER TABLE auto_tag_rules 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            """)
            print("✅ updated_at column added to auto_tag_rules table")
        else:
            print("✅ updated_at column already exists in auto_tag_rules table")
        
        conn.commit()
        print("🎉 Database migration completed successfully!")
        
    except mysql.connector.Error as e:
        print(f"❌ Database migration failed: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ Migration error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_database()
