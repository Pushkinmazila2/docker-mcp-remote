import json
import os
import uuid
import subprocess
import logging
import socket
from pathlib import Path
from typing import Optional

from .models import ServerConfig, AddServerRequest, ServerAuthType
from . import crypto
from .vault_providers import get_vault_provider

logger = logging.getLogger(__name__)

DATA_FILE = Path(os.getenv("DATA_DIR", "/data")) / "servers.json"
KEYS_DIR = Path(os.getenv("KEYS_DIR", "/keys"))

# Получаем hostname контейнера для идентификации
MCP_HUB_HOSTNAME = socket.gethostname()


def _load() -> dict[str, ServerConfig]:
    """Загружает конфигурацию серверов из Vault или локального файла (fallback)"""
    vault_provider = get_vault_provider()
    
    # Пробуем загрузить из Vault
    vault_config = vault_provider.get_servers_config()
    if vault_config:
        logger.info("Loaded servers config from Vault")
        return {k: ServerConfig(**v) for k, v in vault_config.items()}
    
    # Fallback: загружаем из локального файла
    if DATA_FILE.exists():
        logger.info("Loaded servers config from local file (fallback)")
        with open(DATA_FILE) as f:
            raw = json.load(f)
        return {k: ServerConfig(**v) for k, v in raw.items()}
    
    return {}


def _save(servers: dict[str, ServerConfig]) -> None:
    """Сохраняет конфигурацию серверов в Vault и локальный файл (fallback)"""
    vault_provider = get_vault_provider()
    servers_dict = {k: v.model_dump() for k, v in servers.items()}
    
    # Сохраняем в Vault
    if vault_provider.set_servers_config(servers_dict):
        logger.info("Saved servers config to Vault")
    else:
        logger.warning("Failed to save servers config to Vault, using local file")
    
    # Также сохраняем локально как fallback
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(servers_dict, f, indent=2)


def list_servers() -> list[ServerConfig]:
    return list(_load().values())


def get_server(server_id: str, bearer_token: Optional[str] = None) -> Optional[ServerConfig]:
    """Получает сервер и расшифровывает пароль если нужно"""
    server = _load().get(server_id)
    if not server:
        return None
    
    # Расшифровываем пароль если он есть
    if server.password and bearer_token:
        try:
            server.password = crypto.decrypt_with_bearer(server.password, bearer_token)
        except:
            # Если не удалось расшифровать bearer токеном, пробуем мастер-ключом
            try:
                server.password = crypto.decrypt_with_master_key(server.password)
            except:
                # Если не удалось расшифровать, оставляем как есть
                pass
    elif server.password:
        try:
            server.password = crypto.decrypt_with_master_key(server.password)
        except:
            pass
    
    return server


def add_server(req: AddServerRequest, bearer_token: Optional[str] = None) -> ServerConfig:
    servers = _load()
    server_id = str(uuid.uuid4())[:8]

    key_name = None
    description = req.description
    final_auth_type = req.auth_type
    final_key_path = None
    final_password = None

        # Если используется пароль, генерируем ключи и устанавливаем их на хост
    if req.auth_type == ServerAuthType.PASSWORD:
        # Генерируем SSH ключ
        key_name = f"key_{server_id}"
        private_key_path = KEYS_DIR / key_name
        KEYS_DIR.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(private_key_path), "-C", f"mcp_hub@{MCP_HUB_HOSTNAME}"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"ssh-keygen failed: {result.stderr}")

        # Читаем приватный и публичный ключи
        private_key_content = private_key_path.read_text()
        pub_key_path = Path(str(private_key_path) + ".pub")
        pub_key = pub_key_path.read_text().strip()
        
        # Сохраняем ключ в Vault (только в Vault, без локального хранения)
        vault_provider = get_vault_provider()
        if not vault_provider.set_ssh_key(key_name, private_key_content, pub_key):
            raise RuntimeError(f"Failed to save SSH key {key_name} to Vault")
        
        logger.info(f"SSH key {key_name} saved to Vault")
        
        # Сохраняем метаданные ключа
        metadata = {
            "server_id": server_id,
            "server_name": req.name,
            "server_host": req.host,
            "created_at": str(uuid.uuid4()),  # timestamp placeholder
            "mcp_hub_hostname": MCP_HUB_HOSTNAME
        }
        vault_provider.set_ssh_key_metadata(key_name, metadata)
        
        # Удаляем локальные файлы
        private_key_path.unlink()
        pub_key_path.unlink()

                # Подключаемся по паролю и устанавливаем ключ
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=req.host,
                port=req.port,
                username=req.username,
                password=req.password,
                timeout=10
            )
            
                        # Создаем .ssh директорию и добавляем ключ с идентификацией mcp_hub
            # Добавляем комментарий с hostname контейнера для идентификации
            key_with_comment = f"{pub_key.rsplit(' ', 1)[0]} mcp_hub@{MCP_HUB_HOSTNAME}"
            commands = [
                "mkdir -p ~/.ssh",
                "chmod 700 ~/.ssh",
                f"echo '{key_with_comment}' >> ~/.ssh/authorized_keys",
                "chmod 600 ~/.ssh/authorized_keys"
            ]
            for cmd in commands:
                stdin, stdout, stderr = client.exec_command(cmd)
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    err = stderr.read().decode().strip()
                    raise RuntimeError(f"Failed to setup SSH key: {err}")
            
            client.close()
            
            # Меняем тип аутентификации на ключ
            final_auth_type = ServerAuthType.GENERATE_KEY
            final_key_path = str(private_key_path)
            description = (req.description or "") + f"\n[SSH key auto-installed on {req.host}]"
            # Пароль больше не нужен, так как используем ключ
            final_password = None
            
        except Exception as e:
            # Если не удалось установить ключ, сохраняем пароль
            final_password = req.password
            description = (req.description or "") + f"\n[Warning: Failed to install SSH key: {e}. Using password auth.]"
    
    elif req.auth_type == ServerAuthType.KEY_PATH:
        final_key_path = req.key_path
    
    elif req.auth_type == ServerAuthType.GENERATE_KEY:
        # Генерируем SSH ключ без установки
        key_name = f"key_{server_id}"
        private_key_path = KEYS_DIR / key_name
        KEYS_DIR.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(private_key_path), "-C", f"mcp_hub@{MCP_HUB_HOSTNAME}"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"ssh-keygen failed: {result.stderr}")

        # Читаем ключи
        private_key_content = private_key_path.read_text()
        pub_key_path = Path(str(private_key_path) + ".pub")
        pub_key = pub_key_path.read_text().strip()
        
        # Сохраняем ключ в Vault (только в Vault)
        vault_provider = get_vault_provider()
        if not vault_provider.set_ssh_key(key_name, private_key_content, pub_key):
            raise RuntimeError(f"Failed to save SSH key {key_name} to Vault")
        
        logger.info(f"SSH key {key_name} saved to Vault")
        
        # Сохраняем метаданные ключа
        metadata = {
            "server_id": server_id,
            "server_name": req.name,
            "server_host": req.host,
            "created_at": str(uuid.uuid4()),
            "mcp_hub_hostname": MCP_HUB_HOSTNAME
        }
        vault_provider.set_ssh_key_metadata(key_name, metadata)
        
        # Удаляем локальные файлы
        private_key_path.unlink()
        pub_key_path.unlink()
        
        # Возвращаем публичный ключ в описании с идентификацией mcp_hub
        description = (req.description or "") + f"\n[PUBLIC KEY - add to authorized_keys on host]:\n{pub_key}"
        final_key_path = key_name  # Теперь храним только имя ключа, не путь

        # Шифруем пароль если он есть и передан bearer токен
    encrypted_password = None
    if final_password and bearer_token:
        encrypted_password = crypto.encrypt_with_bearer(final_password, bearer_token)
    elif final_password:
        # Если bearer не передан, используем мастер-ключ
        encrypted_password = crypto.encrypt_with_master_key(final_password)
    
    config = ServerConfig(
        id=server_id,
        name=req.name,
        host=req.host,
        port=req.port,
        username=req.username,
        auth_type=final_auth_type,
        password=encrypted_password,
        key_path=final_key_path,
        generated_key_name=key_name,
        description=description,
        tags=req.tags,
    )

    servers[server_id] = config
    _save(servers)
    return config


def remove_server(server_id: str) -> bool:
    servers = _load()
    if server_id not in servers:
        return False
    cfg = servers.pop(server_id)
    
    # Удаляем сгенерированные ключи из Vault
    if cfg.generated_key_name:
        vault_provider = get_vault_provider()
        
        if vault_provider.delete_ssh_key(cfg.generated_key_name):
            logger.info(f"SSH key {cfg.generated_key_name} deleted from Vault")
        else:
            logger.warning(f"Failed to delete SSH key {cfg.generated_key_name} from Vault")
    
    _save(servers)
    return True
