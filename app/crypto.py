import os
import base64
import secrets
import logging
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from .vault_providers import get_vault_provider

logger = logging.getLogger(__name__)

# Получаем провайдер хранилища
vault_provider = get_vault_provider()

# Пути к локальным файлам (для обратной совместимости)
MASTER_KEY_FILE = Path(os.getenv("DATA_DIR", "/data")) / ".master_key"
SALT_FILE = Path(os.getenv("DATA_DIR", "/data")) / ".salt"
KEYS_DIR = Path(os.getenv("KEYS_DIR", "/keys"))

def _ensure_master_key() -> bytes:
    """Создает или загружает мастер-ключ из выбранного хранилища"""
    # Пытаемся получить из vault
    master_key = vault_provider.get_master_key()
    
    if master_key:
        logger.info("✅ Master key loaded from vault")
        return master_key
    
    # Генерируем новый мастер-ключ
    logger.info("🔑 Generating new master key...")
    master_key = secrets.token_bytes(32)
    
    # Сохраняем в vault
    if vault_provider.set_master_key(master_key):
        logger.info("✅ Master key saved to vault")
    else:
        logger.error("❌ Failed to save master key to vault")
    
    return master_key

def _ensure_salt() -> bytes:
    """Создает или загружает соль для KDF из выбранного хранилища"""
    # Пытаемся получить из vault
    salt = vault_provider.get_salt()
    
    if salt:
        logger.info("✅ Salt loaded from vault")
        return salt
    
    # Генерируем новую соль
    logger.info("🧂 Generating new salt...")
    salt = secrets.token_bytes(32)
    
    # Сохраняем в vault
    if vault_provider.set_salt(salt):
        logger.info("✅ Salt saved to vault")
    else:
        logger.error("❌ Failed to save salt to vault")
    
    return salt

# Инициализируем при импорте
MASTER_KEY = _ensure_master_key()
SALT = _ensure_salt()

def derive_key_from_bearer(bearer_token: str) -> bytes:
    """
    Получает ключ шифрования из Bearer токена через KDF
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(bearer_token.encode()))
    return key

def encrypt_with_bearer(data: str, bearer_token: str) -> str:
    """
    Шифрует данные используя ключ, производный от Bearer токена
    """
    if not data:
        return data
    
    key = derive_key_from_bearer(bearer_token)
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_with_bearer(encrypted_data: str, bearer_token: str) -> str:
    """
    Расшифровывает данные используя ключ, производный от Bearer токена
    """
    if not encrypted_data:
        return encrypted_data
    
    try:
        key = derive_key_from_bearer(bearer_token)
        f = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt data: {e}")

def encrypt_with_master_key(data: str) -> str:
    """
    Шифрует данные мастер-ключом (для системных данных)
    """
    if not data:
        return data
    
    key = base64.urlsafe_b64encode(MASTER_KEY)
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_with_master_key(encrypted_data: str) -> str:
    """
    Расшифровывает данные мастер-ключом
    """
    if not encrypted_data:
        return encrypted_data
    
    try:
        key = base64.urlsafe_b64encode(MASTER_KEY)
        f = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt data: {e}")

def re_encrypt_data(encrypted_data: str, old_bearer: str, new_bearer: str) -> str:
    """
    Перешифровывает данные при смене Bearer токена
    """
    # Расшифровываем старым ключом
    decrypted = decrypt_with_bearer(encrypted_data, old_bearer)
    # Шифруем новым ключом
    return encrypt_with_bearer(decrypted, new_bearer)