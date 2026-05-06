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
    def get_ssh_key_metadata(self, key_name: str) -> Optional[dict]:
        """Получить метаданные SSH ключа (server info, etc)"""
        pass
    
    @abstractmethod
    def set_ssh_key_metadata(self, key_name: str, metadata: dict) -> bool:
        """Сохранить метаданные SSH ключа"""
        pass
    
    @abstractmethod
    def scan_ssh_keys_directory(self, directory: str) -> list[dict]:
        """Сканировать директорию и импортировать SSH ключи с метаданными"""
        pass
    
    @abstractmethod
    def get_servers_config(self) -> Optional[dict]:
        """Получить конфигурацию серверов из Vault"""
        pass
    
    @abstractmethod
    def set_servers_config(self, config: dict) -> bool:
        """Сохранить конфигурацию серверов в Vault"""
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
        # Local provider не должен использоваться для SSH ключей
        logger.warning("LocalFileVaultProvider.get_ssh_key called - SSH keys should be in Vault only")
        return None
    
    def set_ssh_key(self, key_name: str, private_key: str, public_key: str = None) -> bool:
        logger.warning("LocalFileVaultProvider.set_ssh_key called - SSH keys should be in Vault only")
        return False
    
    def delete_ssh_key(self, key_name: str) -> bool:
        logger.warning("LocalFileVaultProvider.delete_ssh_key called - SSH keys should be in Vault only")
        return False
    
    def list_ssh_keys(self) -> list[str]:
        logger.warning("LocalFileVaultProvider.list_ssh_keys called - SSH keys should be in Vault only")
        return []
    
    def is_available(self) -> bool:
        return True
    
    def get_ssh_key_metadata(self, key_name: str) -> Optional[dict]:
        logger.warning("LocalFileVaultProvider.get_ssh_key_metadata called - not supported")
        return None
    
    def set_ssh_key_metadata(self, key_name: str, metadata: dict) -> bool:
        logger.warning("LocalFileVaultProvider.set_ssh_key_metadata called - not supported")
        return False
    
    def scan_ssh_keys_directory(self, directory: str) -> list[dict]:
        logger.warning("LocalFileVaultProvider.scan_ssh_keys_directory called - not supported")
        return []
    
    def get_servers_config(self) -> Optional[dict]:
        logger.warning("LocalFileVaultProvider.get_servers_config called - not supported")
        return None
    
    def set_servers_config(self, config: dict) -> bool:
        logger.warning("LocalFileVaultProvider.set_servers_config called - not supported")
        return False


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
    
    def get_ssh_key_metadata(self, key_name: str) -> Optional[dict]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=f"{self.vault_path}/ssh-keys/{key_name}"
            )
            return response['data']['data'].get('metadata', {})
        except Exception as e:
            logger.debug(f"Metadata for SSH key {key_name} not found in Vault: {e}")
            return None
    
    def set_ssh_key_metadata(self, key_name: str, metadata: dict) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            # Получаем текущий ключ
            response = client.secrets.kv.v2.read_secret_version(
                path=f"{self.vault_path}/ssh-keys/{key_name}"
            )
            current_data = response['data']['data']
            
            # Добавляем метаданные
            current_data['metadata'] = metadata
            
            client.secrets.kv.v2.create_or_update_secret(
                path=f"{self.vault_path}/ssh-keys/{key_name}",
                secret=current_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata for SSH key {key_name}: {e}")
            return False
    
    def scan_ssh_keys_directory(self, directory: str) -> list[dict]:
        """Сканирует директорию и импортирует SSH ключи в Vault"""
        from pathlib import Path
        import json
        
        keys_dir = Path(directory)
        if not keys_dir.exists():
            logger.warning(f"SSH keys directory {directory} does not exist")
            return []
        
        imported_keys = []
        
        # Ищем config.json с метаданными
        config_file = keys_dir / "config.json"
        metadata_map = {}
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config_data = json.load(f)
                    metadata_map = config_data.get('keys', {})
                logger.info(f"Loaded metadata for {len(metadata_map)} keys from config.json")
            except Exception as e:
                logger.warning(f"Failed to load config.json: {e}")
        
        # Сканируем все приватные ключи
        for key_file in keys_dir.iterdir():
            if key_file.is_file() and not key_file.name.endswith('.pub') and key_file.name != 'config.json':
                try:
                    key_name = key_file.name
                    private_key = key_file.read_text()
                    
                    # Ищем публичный ключ
                    pub_file = keys_dir / f"{key_name}.pub"
                    public_key = None
                    if pub_file.exists():
                        public_key = pub_file.read_text().strip()
                    
                    # Получаем метаданные из config.json
                    metadata = metadata_map.get(key_name, {})
                    
                    # Сохраняем в Vault
                    if self.set_ssh_key(key_name, private_key, public_key):
                        if metadata:
                            self.set_ssh_key_metadata(key_name, metadata)
                        
                        imported_keys.append({
                            'key_name': key_name,
                            'has_public_key': public_key is not None,
                            'metadata': metadata
                        })
                        logger.info(f"Imported SSH key {key_name} to Vault")
                    
                except Exception as e:
                    logger.error(f"Failed to import SSH key {key_file.name}: {e}")
        
        return imported_keys
    
    def get_servers_config(self) -> Optional[dict]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=f"{self.vault_path}/servers"
            )
            return response['data']['data']
        except Exception as e:
            logger.debug(f"Servers config not found in Vault: {e}")
            return None
    
    def set_servers_config(self, config: dict) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.secrets.kv.v2.create_or_update_secret(
                path=f"{self.vault_path}/servers",
                secret=config
            )
            logger.info("Servers config saved to Vault")
            return True
        except Exception as e:
            logger.error(f"Failed to save servers config to Vault: {e}")
            return False


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
    
    def get_ssh_key_metadata(self, key_name: str) -> Optional[dict]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            import json
            response = client.get_secret_value(SecretId=f"{self.secret_name}/ssh-keys/{key_name}")
            secret = json.loads(response['SecretString'])
            return secret.get('metadata', {})
        except Exception as e:
            logger.debug(f"Metadata for SSH key {key_name} not found in AWS: {e}")
            return None
    
    def set_ssh_key_metadata(self, key_name: str, metadata: dict) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            import json
            response = client.get_secret_value(SecretId=f"{self.secret_name}/ssh-keys/{key_name}")
            secret_data = json.loads(response['SecretString'])
            secret_data['metadata'] = metadata
            
            client.update_secret(
                SecretId=f"{self.secret_name}/ssh-keys/{key_name}",
                SecretString=json.dumps(secret_data)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata for SSH key {key_name} to AWS: {e}")
            return False
    
    def scan_ssh_keys_directory(self, directory: str) -> list[dict]:
        from pathlib import Path
        import json
        
        keys_dir = Path(directory)
        if not keys_dir.exists():
            logger.warning(f"SSH keys directory {directory} does not exist")
            return []
        
        imported_keys = []
        config_file = keys_dir / "config.json"
        metadata_map = {}
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config_data = json.load(f)
                    metadata_map = config_data.get('keys', {})
                logger.info(f"Loaded metadata for {len(metadata_map)} keys from config.json")
            except Exception as e:
                logger.warning(f"Failed to load config.json: {e}")
        
        for key_file in keys_dir.iterdir():
            if key_file.is_file() and not key_file.name.endswith('.pub') and key_file.name != 'config.json':
                try:
                    key_name = key_file.name
                    private_key = key_file.read_text()
                    
                    pub_file = keys_dir / f"{key_name}.pub"
                    public_key = None
                    if pub_file.exists():
                        public_key = pub_file.read_text().strip()
                    
                    metadata = metadata_map.get(key_name, {})
                    
                    if self.set_ssh_key(key_name, private_key, public_key):
                        if metadata:
                            self.set_ssh_key_metadata(key_name, metadata)
                        
                        imported_keys.append({
                            'key_name': key_name,
                            'has_public_key': public_key is not None,
                            'metadata': metadata
                        })
                        logger.info(f"Imported SSH key {key_name} to AWS")
                    
                except Exception as e:
                    logger.error(f"Failed to import SSH key {key_file.name}: {e}")
        
        return imported_keys
    
    def get_servers_config(self) -> Optional[dict]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            import json
            response = client.get_secret_value(SecretId=f"{self.secret_name}/servers")
            return json.loads(response['SecretString'])
        except Exception as e:
            logger.debug(f"Servers config not found in AWS: {e}")
            return None
    
    def set_servers_config(self, config: dict) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            import json
            try:
                client.update_secret(
                    SecretId=f"{self.secret_name}/servers",
                    SecretString=json.dumps(config)
                )
            except:
                client.create_secret(
                    Name=f"{self.secret_name}/servers",
                    SecretString=json.dumps(config)
                )
            logger.info("Servers config saved to AWS")
            return True
        except Exception as e:
            logger.error(f"Failed to save servers config to AWS: {e}")
            return False


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
