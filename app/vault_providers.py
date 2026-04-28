"""
Провайдеры для хранения мастер-ключей и соли.
Поддерживает локальное хранилище и внешние Vault системы.
"""
import os
import secrets
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VaultProvider(ABC):
    """Базовый класс для провайдеров хранилищ"""
    
    @abstractmethod
    def get_master_key(self) -> Optional[bytes]:
        """Получить мастер-ключ"""
        pass
    
    @abstractmethod
    def get_salt(self) -> Optional[bytes]:
        """Получить соль"""
        pass
    
    @abstractmethod
    def set_master_key(self, key: bytes) -> bool:
        """Сохранить мастер-ключ"""
        pass
    
    @abstractmethod
    def set_salt(self, salt: bytes) -> bool:
        """Сохранить соль"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Проверить доступность провайдера"""
        pass


class LocalFileVaultProvider(VaultProvider):
    """Локальное хранилище в файлах (по умолчанию)"""
    
    def __init__(self, data_dir: str = "/data"):
        self.master_key_file = Path(data_dir) / ".master_key"
        self.salt_file = Path(data_dir) / ".salt"
    
    def get_master_key(self) -> Optional[bytes]:
        if self.master_key_file.exists():
            return self.master_key_file.read_bytes()
        return None
    
    def get_salt(self) -> Optional[bytes]:
        if self.salt_file.exists():
            return self.salt_file.read_bytes()
        return None
    
    def set_master_key(self, key: bytes) -> bool:
        try:
            self.master_key_file.parent.mkdir(parents=True, exist_ok=True)
            self.master_key_file.write_bytes(key)
            os.chmod(self.master_key_file, 0o600)
            return True
        except Exception as e:
            logger.error(f"Failed to save master key: {e}")
            return False
    
    def set_salt(self, salt: bytes) -> bool:
        try:
            self.salt_file.parent.mkdir(parents=True, exist_ok=True)
            self.salt_file.write_bytes(salt)
            os.chmod(self.salt_file, 0o600)
            return True
        except Exception as e:
            logger.error(f"Failed to save salt: {e}")
            return False
    
    def is_available(self) -> bool:
        return True


class HashiCorpVaultProvider(VaultProvider):
    """HashiCorp Vault провайдер"""
    
    def __init__(self):
        self.vault_addr = os.getenv("VAULT_ADDR")
        self.vault_token = os.getenv("VAULT_TOKEN")
        self.vault_path = os.getenv("VAULT_SECRET_PATH", "secret/data/docker-mcp-hub")
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(
                    url=self.vault_addr,
                    token=self.vault_token
                )
            except ImportError:
                logger.error("hvac library not installed. Install with: pip install hvac")
                return None
        return self._client
    
    def get_master_key(self) -> Optional[bytes]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=self.vault_path
            )
            master_key_b64 = response['data']['data'].get('master_key')
            if master_key_b64:
                import base64
                return base64.b64decode(master_key_b64)
        except Exception as e:
            logger.error(f"Failed to get master key from Vault: {e}")
        return None
    
    def get_salt(self) -> Optional[bytes]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=self.vault_path
            )
            salt_b64 = response['data']['data'].get('salt')
            if salt_b64:
                import base64
                return base64.b64decode(salt_b64)
        except Exception as e:
            logger.error(f"Failed to get salt from Vault: {e}")
        return None
    
    def set_master_key(self, key: bytes) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            import base64
            # Получаем текущие данные
            current_data = {}
            try:
                response = client.secrets.kv.v2.read_secret_version(path=self.vault_path)
                current_data = response['data']['data']
            except:
                pass
            
            # Обновляем мастер-ключ
            current_data['master_key'] = base64.b64encode(key).decode()
            
            client.secrets.kv.v2.create_or_update_secret(
                path=self.vault_path,
                secret=current_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save master key to Vault: {e}")
            return False
    
    def set_salt(self, salt: bytes) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            import base64
            # Получаем текущие данные
            current_data = {}
            try:
                response = client.secrets.kv.v2.read_secret_version(path=self.vault_path)
                current_data = response['data']['data']
            except:
                pass
            
            # Обновляем соль
            current_data['salt'] = base64.b64encode(salt).decode()
            
            client.secrets.kv.v2.create_or_update_secret(
                path=self.vault_path,
                secret=current_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save salt to Vault: {e}")
            return False
    
    def is_available(self) -> bool:
        return bool(self.vault_addr and self.vault_token)


class AWSSecretsManagerProvider(VaultProvider):
    """AWS Secrets Manager провайдер"""
    
    def __init__(self):
        self.secret_name = os.getenv("AWS_SECRET_NAME", "docker-mcp-hub/master-keys")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client('secretsmanager', region_name=self.region)
            except ImportError:
                logger.error("boto3 library not installed. Install with: pip install boto3")
                return None
        return self._client
    
    def get_master_key(self) -> Optional[bytes]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            import json
            import base64
            response = client.get_secret_value(SecretId=self.secret_name)
            secret = json.loads(response['SecretString'])
            master_key_b64 = secret.get('master_key')
            if master_key_b64:
                return base64.b64decode(master_key_b64)
        except Exception as e:
            logger.error(f"Failed to get master key from AWS Secrets Manager: {e}")
        return None
    
    def get_salt(self) -> Optional[bytes]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            import json
            import base64
            response = client.get_secret_value(SecretId=self.secret_name)
            secret = json.loads(response['SecretString'])
            salt_b64 = secret.get('salt')
            if salt_b64:
                return base64.b64decode(salt_b64)
        except Exception as e:
            logger.error(f"Failed to get salt from AWS Secrets Manager: {e}")
        return None
    
    def set_master_key(self, key: bytes) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            import json
            import base64
            
            # Получаем текущий секрет
            current_secret = {}
            try:
                response = client.get_secret_value(SecretId=self.secret_name)
                current_secret = json.loads(response['SecretString'])
            except:
                pass
            
            # Обновляем мастер-ключ
            current_secret['master_key'] = base64.b64encode(key).decode()
            
            # Сохраняем
            try:
                client.update_secret(
                    SecretId=self.secret_name,
                    SecretString=json.dumps(current_secret)
                )
            except:
                # Если секрет не существует, создаем
                client.create_secret(
                    Name=self.secret_name,
                    SecretString=json.dumps(current_secret)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to save master key to AWS Secrets Manager: {e}")
            return False
    
    def set_salt(self, salt: bytes) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            import json
            import base64
            
            # Получаем текущий секрет
            current_secret = {}
            try:
                response = client.get_secret_value(SecretId=self.secret_name)
                current_secret = json.loads(response['SecretString'])
            except:
                pass
            
            # Обновляем соль
            current_secret['salt'] = base64.b64encode(salt).decode()
            
            # Сохраняем
            try:
                client.update_secret(
                    SecretId=self.secret_name,
                    SecretString=json.dumps(current_secret)
                )
            except:
                client.create_secret(
                    Name=self.secret_name,
                    SecretString=json.dumps(current_secret)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to save salt to AWS Secrets Manager: {e}")
            return False
    
    def is_available(self) -> bool:
        # Проверяем наличие AWS credentials
        return bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE"))


def get_vault_provider() -> VaultProvider:
    """
    Определяет и возвращает подходящий провайдер на основе переменных окружения.
    
    Приоритет:
    1. HashiCorp Vault (если VAULT_ADDR установлен)
    2. AWS Secrets Manager (если AWS_SECRET_NAME установлен)
    3. Local File (по умолчанию)
    """
    vault_type = os.getenv("VAULT_TYPE", "local").lower()
    
    if vault_type == "hashicorp" or os.getenv("VAULT_ADDR"):
        provider = HashiCorpVaultProvider()
        if provider.is_available():
            logger.info("🔐 Using HashiCorp Vault for master keys storage")
            return provider
        logger.warning("HashiCorp Vault configured but not available, falling back to local")
    
    if vault_type == "aws" or os.getenv("AWS_SECRET_NAME"):
        provider = AWSSecretsManagerProvider()
        if provider.is_available():
            logger.info("🔐 Using AWS Secrets Manager for master keys storage")
            return provider
        logger.warning("AWS Secrets Manager configured but not available, falling back to local")
    
    logger.info("🔐 Using Local File storage for master keys")
    return LocalFileVaultProvider(os.getenv("DATA_DIR", "/data"))
