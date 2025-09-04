import mysql.connector
import bcrypt
import datetime
import random
from typing import Optional, Dict, Any
from config.database import DB_CONFIG

class User:
    """User model for dashboard users"""
    
    def __init__(self, id: int = None, username: str = None, email: str = None, 
                 password_hash: str = None, failed_attempts: int = 0, 
                 locked_until: datetime.datetime = None, reset_token: str = None,
                 reset_token_expiry: datetime.datetime = None, verification_code: str = None,
                 verification_expiry: datetime.datetime = None, is_verified: bool = False,
                 created_at: datetime.datetime = None, last_login: datetime.datetime = None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.failed_attempts = failed_attempts
        self.locked_until = locked_until
        self.reset_token = reset_token
        self.reset_token_expiry = reset_token_expiry
        self.verification_code = verification_code
        self.verification_expiry = verification_expiry
        self.is_verified = is_verified
        self.created_at = created_at
        self.last_login = last_login

    @staticmethod
    def create_database():
        """Create the dashboard_users table"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
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
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def authenticate(username_or_email: str, password: str) -> Optional['User']:
        """Authenticate user with username/email and password"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM dashboard_users WHERE username=%s OR email=%s", 
                         (username_or_email, username_or_email))
            row = cursor.fetchone()
            
            if not row:
                return None

            # Check if user is verified
            if not row['is_verified']:
                return None

            now = datetime.datetime.now()
            if row['locked_until'] and now < row['locked_until']:
                return None

            if bcrypt.checkpw(password.encode(), row['password_hash'].encode()):
                # Successful login - reset failed attempts
                cursor.execute(
                    "UPDATE dashboard_users SET failed_attempts=0, locked_until=NULL, last_login=NOW() WHERE id=%s",
                    (row['id'],)
                )
                conn.commit()
                
                return User(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    failed_attempts=0,
                    locked_until=None,
                    reset_token=row['reset_token'],
                    reset_token_expiry=row['reset_token_expiry'],
                    verification_code=row['verification_code'],
                    verification_expiry=row['verification_expiry'],
                    is_verified=row['is_verified'],
                    created_at=row['created_at'],
                    last_login=now
                )
            else:
                # Failed login - increment failed attempts
                attempts = row['failed_attempts'] + 1
                lock_time = None
                if attempts >= 5:
                    lock_time = now + datetime.timedelta(minutes=10)
                    
                cursor.execute(
                    "UPDATE dashboard_users SET failed_attempts=%s, locked_until=%s WHERE id=%s",
                    (attempts, lock_time, row['id'])
                )
                conn.commit()
                return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_user(username: str, email: str, password: str) -> Optional['User']:
        """Create a new user (unverified)"""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO dashboard_users (username, email, password_hash, is_verified) VALUES (%s, %s, %s, FALSE)",
                (username, email, password_hash)
            )
            conn.commit()
            
            user_id = cursor.lastrowid
            return User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                is_verified=False,
                created_at=datetime.datetime.now()
            )
        except mysql.connector.errors.IntegrityError:
            return None  # Username or email already exists
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def generate_verification_code(email: str) -> Optional[str]:
        """Generate verification code for user"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT id FROM dashboard_users WHERE email=%s", (email,))
            row = cursor.fetchone()
            
            if not row:
                return None

            # Generate 6-digit verification code
            code = f"{random.randint(0, 999999):06d}"
            expiry = datetime.datetime.now() + datetime.timedelta(minutes=15)
            
            cursor.execute(
                "UPDATE dashboard_users SET verification_code=%s, verification_expiry=%s WHERE id=%s",
                (code, expiry, row['id'])
            )
            conn.commit()
            
            return code
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def verify_user(email: str, code: str) -> bool:
        """Verify user with verification code"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                "SELECT id, verification_expiry FROM dashboard_users WHERE email=%s AND verification_code=%s",
                (email, code)
            )
            row = cursor.fetchone()
            
            if not row or row['verification_expiry'] < datetime.datetime.now():
                return False

            cursor.execute(
                "UPDATE dashboard_users SET is_verified=TRUE, verification_code=NULL, verification_expiry=NULL WHERE id=%s",
                (row['id'],)
            )
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def is_user_verified(email: str) -> bool:
        """Check if user is verified"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT is_verified FROM dashboard_users WHERE email=%s", (email,))
            row = cursor.fetchone()
            
            if not row:
                return False
                
            return bool(row['is_verified'])
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def generate_reset_token(email: str) -> Optional[str]:
        """Generate password reset token for user"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT id FROM dashboard_users WHERE email=%s", (email,))
            row = cursor.fetchone()
            
            if not row:
                return None

            # Generate 4-digit PIN
            token = f"{random.randint(0, 9999):04d}"
            expiry = datetime.datetime.now() + datetime.timedelta(minutes=20)
            
            cursor.execute(
                "UPDATE dashboard_users SET reset_token=%s, reset_token_expiry=%s WHERE id=%s",
                (token, expiry, row['id'])
            )
            conn.commit()
            
            return token
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def reset_password(email: str, token: str, new_password: str) -> bool:
        """Reset password using token"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                "SELECT id, reset_token_expiry FROM dashboard_users WHERE email=%s AND reset_token=%s",
                (email, token)
            )
            row = cursor.fetchone()
            
            if not row or row['reset_token_expiry'] < datetime.datetime.now():
                return False

            password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            cursor.execute(
                "UPDATE dashboard_users SET password_hash=%s, reset_token=NULL, reset_token_expiry=NULL WHERE id=%s",
                (password_hash, row['id'])
            )
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        """Get user by ID"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM dashboard_users WHERE id=%s", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return User(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                password_hash=row['password_hash'],
                failed_attempts=row['failed_attempts'],
                locked_until=row['locked_until'],
                reset_token=row['reset_token'],
                reset_token_expiry=row['reset_token_expiry'],
                verification_code=row['verification_code'],
                verification_expiry=row['verification_expiry'],
                is_verified=row['is_verified'],
                created_at=row['created_at'],
                last_login=row['last_login']
            )
        finally:
            cursor.close()
            conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'failed_attempts': self.failed_attempts,
            'locked_until': self.locked_until,
            'created_at': self.created_at,
            'last_login': self.last_login
        } 