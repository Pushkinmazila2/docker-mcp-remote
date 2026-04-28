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
    def get_token(self, key: str) -> Optional[str]:
        """Получить токен по ключу"""
        pass
    
    @abstractmethod
    def set_token(self, key: str, token: str) -> bool:
        """Сохранить токен"""
        pass
    
    @abstractmethod
    def delete_token(self, key: str) -> bool:
        """Удалить токен"""
        pass
    
    @abstractmethod
    def list_token_keys(self) -> list[str]:
        """Получить список всех ключей токенов"""
        pass
    
    @abstractmethod
    def get_ssh_key(self, key_name: str) -> Optional[str]:
        """Получить SSH приватный ключ"""
        pass
    
    @abstractmethod
    def set_ssh_key(self, key_name: str, private_key: str, public_key: str = None) -> bool:
        """Сохранить SSH ключ (приватный и опционально публичный)"""
        pass
    
    @abstractmethod
    def delete_ssh_key(self, key_name: str) -> bool:
        """Удалить SSH ключ"""
        pass
    
    @abstractmethod
    def list_ssh_keys(self) -> list[str]:
        """Получить список всех SSH ключей"""
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
    
    def get_token(self, key: str) -> Optional[str]:
        token_file = Path(self.master_key_file.parent) / f".token_{key}"
        if token_file.exists():
            return token_file.read_text().strip()
        return None
    
    def set_token(self, key: str, token: str) -> bool:
        try:
            token_file = Path(self.master_key_file.parent) / f".token_{key}"
            token_file.parent.mkdir(parents=True, exist_ok=True)
            token_file.write_text(token)
            os.chmod(token_file, 0o600)
            return True
        except Exception as e:
            logger.error(f"Failed to save token {key}: {e}")
            return False
    
    def delete_token(self, key: str) -> bool:
        try:
            token_file = Path(self.master_key_file.parent) / f".token_{key}"
            if token_file.exists():
                token_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete token {key}: {e}")
            return False
    
    def list_token_keys(self) -> list[str]:
        try:
            token_files = Path(self.master_key_file.parent).glob(".token_*")
            return [f.name.replace(".token_", "") for f in token_files]
        except Exception as e:
            logger.error(f"Failed to list tokens: {e}")
            return []
    
    def get_ssh_key(self, key_name: str) -> Optional[str]:
        from pathlib import Path
        keys_dir = Path(os.getenv("KEYS_DIR", "/keys"))
        key_file = keys_dir / key_name
        if key_file.exists():
            return key_file.read_text()
        return None
    
    def set_ssh_key(self, key_name: str, private_key: str, public_key: str = None) -> bool:
        try:
            from pathlib import Path
            keys_dir = Path(os.getenv("KEYS_DIR", "/keys"))
            keys_dir.mkdir(parents=True, exist_ok=True)
            
            key_file = keys_dir / key_name
            key_file.write_text(private_key)
            os.chmod(key_file, 0o600)
            
            if public_key:
                pub_file = keys_dir / f"{key_name}.pub"
                pub_file.write_text(public_key)
                os.chmod(pub_file, 0o644)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save SSH key {key_name}: {e}")
            return False
    
    def delete_ssh_key(self, key_name: str) -> bool:
        try:
            from pathlib import Path
            keys_dir = Path(os.getenv("KEYS_DIR", "/keys"))
            key_file = keys_dir / key_name
            pub_file = keys_dir / f"{key_name}.pub"
            
            if key_file.exists():
                key_file.unlink()
            if pub_file.exists():
                pub_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete SSH key {key_name}: {e}")
            return False
    
    def list_ssh_keys(self) -> list[str]:
        try:
            from pathlib import Path
            keys_dir = Path(os.getenv("KEYS_DIR", "/keys"))
            if not keys_dir.exists():
                return []
            # Возвращаем только приватные ключи (без .pub)
            return [f.name for f in keys_dir.iterdir() if f.is_file() and not f.name.endswith('.pub')]
        except Exception as e:
            logger.error(f"Failed to list SSH keys: {e}")
            return []
    
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
    
    def get_token(self, key: str) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=f"{self.vault_path}/tokens"
            )
            return response['data']['data'].get(key)
        except Exception as e:
            logger.debug(f"Token {key} not found in Vault: {e}")
            return None
    
    def set_token(self, key: str, token: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            # Получаем текущие токены
            current_tokens = {}
            try:
                response = client.secrets.kv.v2.read_secret_version(
                    path=f"{self.vault_path}/tokens"
                )
                current_tokens = response['data']['data']
            except:
                pass
            
            # Добавляем новый токен
            current_tokens[key] = token
            
            client.secrets.kv.v2.create_or_update_secret(
                path=f"{self.vault_path}/tokens",
                secret=current_tokens
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save token {key} to Vault: {e}")
            return False
    
    def delete_token(self, key: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            # Получаем текущие токены
            response = client.secrets.kv.v2.read_secret_version(
                path=f"{self.vault_path}/tokens"
            )
            current_tokens = response['data']['data']
            
            # Удаляем токен
            if key in current_tokens:
                del current_tokens[key]
                
                client.secrets.kv.v2.create_or_update_secret(
                    path=f"{self.vault_path}/tokens",
                    secret=current_tokens
                )
            return True
        except Exception as e:
            logger.error(f"Failed to delete token {key} from Vault: {e}")
            return False
    
    def list_token_keys(self) -> list[str]:
        client = self._get_client()
        if not client:
            return []
        
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=f"{self.vault_path}/tokens"
            )
            return list(response['data']['data'].keys())
        except Exception as e:
            logger.debug(f"No tokens found in Vault: {e}")
            return []
    
    def get_ssh_key(self, key_name: str) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=f"{self.vault_path}/ssh-keys/{key_name}"
            )
            return response['data']['data'].get('private_key')
        except Exception as e:
            logger.debug(f"SSH key {key_name} not found in Vault: {e}")
            return None
    
    def set_ssh_key(self, key_name: str, private_key: str, public_key: str = None) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            secret_data = {'private_key': private_key}
            if public_key:
                secret_data['public_key'] = public_key
            
            client.secrets.kv.v2.create_or_update_secret(
                path=f"{self.vault_path}/ssh-keys/{key_name}",
                secret=secret_data
            )
            logger.info(f"SSH key {key_name} saved to Vault")
            return True
        except Exception as e:
            logger.error(f"Failed to save SSH key {key_name} to Vault: {e}")
            return False
    
    def delete_ssh_key(self, key_name: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=f"{self.vault_path}/ssh-keys/{key_name}"
            )
            logger.info(f"SSH key {key_name} deleted from Vault")
            return True
        except Exception as e:
            logger.error(f"Failed to delete SSH key {key_name} from Vault: {e}")
            return False
    
    def list_ssh_keys(self) -> list[str]:
        client = self._get_client()
        if not client:
            return []
        
        try:
            response = client.secrets.kv.v2.list_secrets(
                path=f"{self.vault_path}/ssh-keys"
            )
            return response['data']['keys']
        except Exception as e:
            logger.debug(f"No SSH keys found in Vault: {e}")
            return []
    
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
    
    def get_token(self, key: str) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            import json
            response = client.get_secret_value(SecretId=f"{self.secret_name}/tokens")
            tokens = json.loads(response['SecretString'])
            return tokens.get(key)
        except Exception as e:
            logger.debug(f"Token {key} not found in AWS: {e}")
            return None
    
    def set_token(self, key: str, token: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            import json
            
            # Получаем текущие токены
            current_tokens = {}
            try:
                response = client.get_secret_value(SecretId=f"{self.secret_name}/tokens")
                current_tokens = json.loads(response['SecretString'])
            except:
                pass
            
            # Добавляем новый токен
            current_tokens[key] = token
            
            # Сохраняем
            try:
                client.update_secret(
                    SecretId=f"{self.secret_name}/tokens",
                    SecretString=json.dumps(current_tokens)
                )
            except:
                client.create_secret(
                    Name=f"{self.secret_name}/tokens",
                    SecretString=json.dumps(current_tokens)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to save token {key} to AWS: {e}")
            return False
    
    def delete_token(self, key: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            import json
            response = client.get_secret_value(SecretId=f"{self.secret_name}/tokens")
            current_tokens = json.loads(response['SecretString'])
            
            if key in current_tokens:
                del current_tokens[key]
                client.update_secret(
                    SecretId=f"{self.secret_name}/tokens",
                    SecretString=json.dumps(current_tokens)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to delete token {key} from AWS: {e}")
            return False
    
    def list_token_keys(self) -> list[str]:
        client = self._get_client()
        if not client:
            return []
        
        try:
            import json
            response = client.get_secret_value(SecretId=f"{self.secret_name}/tokens")
            tokens = json.loads(response['SecretString'])
            return list(tokens.keys())
        except Exception as e:
            logger.debug(f"No tokens found in AWS: {e}")
            return []
    
    def get_ssh_key(self, key_name: str) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            import json
            response = client.get_secret_value(SecretId=f"{self.secret_name}/ssh-keys/{key_name}")
            secret = json.loads(response['SecretString'])
            return secret.get('private_key')
        except Exception as e:
            logger.debug(f"SSH key {key_name} not found in AWS: {e}")
            return None
    
    def set_ssh_key(self, key_name: str, private_key: str, public_key: str = None) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            import json
            secret_data = {'private_key': private_key}
            if public_key:
                secret_data['public_key'] = public_key
            
            try:
                client.update_secret(
                    SecretId=f"{self.secret_name}/ssh-keys/{key_name}",
                    SecretString=json.dumps(secret_data)
                )
            except:
                client.create_secret(
                    Name=f"{self.secret_name}/ssh-keys/{key_name}",
                    SecretString=json.dumps(secret_data)
                )
            logger.info(f"SSH key {key_name} saved to AWS")
            return True
        except Exception as e:
            logger.error(f"Failed to save SSH key {key_name} to AWS: {e}")
            return False
    
    def delete_ssh_key(self, key_name: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.delete_secret(
                SecretId=f"{self.secret_name}/ssh-keys/{key_name}",
                ForceDeleteWithoutRecovery=True
            )
            logger.info(f"SSH key {key_name} deleted from AWS")
            return True
        except Exception as e:
            logger.error(f"Failed to delete SSH key {key_name} from AWS: {e}")
            return False
    
    def list_ssh_keys(self) -> list[str]:
        client = self._get_client()
        if not client:
            return []
        
        try:
            response = client.list_secrets(
                Filters=[{'Key': 'name', 'Values': [f"{self.secret_name}/ssh-keys/"]}]
            )
            keys = []
            for secret in response.get('SecretList', []):
                name = secret['Name']
                if name.startswith(f"{self.secret_name}/ssh-keys/"):
                    key_name = name.replace(f"{self.secret_name}/ssh-keys/", "")
                    keys.append(key_name)
            return keys
        except Exception as e:
            logger.debug(f"No SSH keys found in AWS: {e}")
            return []
    
    def is_available(self) -> bool:
        # Проверяем наличие AWS credentials
        return bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE"))


def get_vault_provider() -> VaultProvider:
    """
    Определяет и возвращает подходящий провайдер на основе переменных окружения.
    
    По умолчанию использует HashiCorp Vault, если не указано иное.
    
    Приоритет:
    1. HashiCorp Vault (по умолчанию, если VAULT_ADDR установлен)
    2. AWS Secrets Manager (если VAULT_TYPE=aws)
    3. Local File (если VAULT_TYPE=local)
    """
    vault_type = os.getenv("VAULT_TYPE", "hashicorp").lower()
    
    # По умолчанию пробуем HashiCorp Vault
    if vault_type == "hashicorp":
        provider = HashiCorpVaultProvider()
        if provider.is_available():
            logger.info("🔐 Using HashiCorp Vault for secrets storage")
            return provider
        logger.warning("HashiCorp Vault configured but not available, falling back to local")
    
    if vault_type == "aws":
        provider = AWSSecretsManagerProvider()
        if provider.is_available():
            logger.info("🔐 Using AWS Secrets Manager for secrets storage")
            return provider
        logger.warning("AWS Secrets Manager configured but not available, falling back to local")
    
    logger.info("🔐 Using Local File storage for secrets")
    return LocalFileVaultProvider(os.getenv("DATA_DIR", "/data"))
