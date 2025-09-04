import os
import json
import re

# Try to load environment variables, fallback gracefully if dotenv not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using system environment variables only.")

# Password policy regex
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$')

# Attachment and config directories
ATTACH_DIR = 'attachments'
os.makedirs(ATTACH_DIR, exist_ok=True)
SECRET_FILE = 'secret.key'
CONFIG_FILE = 'config.json'

# Default configuration
DEFAULT_CONFIG = {
    'theme': 'light',
    'default_imap_host': os.getenv('DEFAULT_IMAP_HOST', 'mail2.multinet.com.pk'),
    'session_days': int(os.getenv('SESSION_DAYS', 90)),
    'real_time_monitoring': os.getenv('REAL_TIME_MONITORING', 'true').lower() == 'true',
    'monitoring_interval': int(os.getenv('MONITORING_INTERVAL', 30)),  # 30 seconds
    'progressive_batch_size': int(os.getenv('PROGRESSIVE_BATCH_SIZE', 100)),        # Batch updates: Show emails every 100 emails for better performance
    'progressive_commit_interval': int(os.getenv('PROGRESSIVE_COMMIT_INTERVAL', 100))    # Database commits every 100 emails for optimal performance
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

CONFIG = load_config()

# Email configuration from environment variables
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 465)),
    'username': os.getenv('SMTP_USERNAME', 'your-email@gmail.com'),
    'password': os.getenv('SMTP_PASSWORD', 'your-app-password')  # Use App Password for Gmail
}