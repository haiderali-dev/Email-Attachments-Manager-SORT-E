import os
from cryptography.fernet import Fernet
from config.settings import SECRET_FILE

def load_or_create_key():
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, 'rb') as f:
            return f.read()
    key = Fernet.generate_key()
    with open(SECRET_FILE, 'wb') as f:
        f.write(key)
    return key

FERNET = Fernet(load_or_create_key())

def encrypt_text(plaintext: str) -> bytes:
    return FERNET.encrypt(plaintext.encode())

def decrypt_text(token: bytes) -> str:
    return FERNET.decrypt(token).decode()