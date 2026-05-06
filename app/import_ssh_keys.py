"""
Утилита для импорта SSH ключей из директории в Vault.
Сканирует директорию с ключами и импортирует их в Vault с метаданными.
"""
import os
import sys
import logging
from pathlib import Path

from .vault_providers import get_vault_provider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_keys_from_directory(directory: str = None) -> dict:
    """
    Импортирует SSH ключи из указанной директории в Vault.
    
    Ожидаемая структура директории:
    /keys/
      ├── config.json          # Опциональный файл с метаданными
      ├── key_abc123           # Приватный ключ
      ├── key_abc123.pub       # Публичный ключ
      ├── key_def456
      └── key_def456.pub
    
    Формат config.json:
    {
      "keys": {
        "key_abc123": {
          "server_id": "abc123",
          "server_name": "Production Server",
          "server_host": "prod.example.com",
          "created_at": "2024-01-01T00:00:00Z",
          "mcp_hub_hostname": "docker-mcp-hub"
        }
      }
    }
    
    Args:
        directory: Путь к директории с ключами. По умолчанию используется KEYS_DIR из env.
    
    Returns:
        dict: Результаты импорта с информацией о каждом ключе
    """
    if directory is None:
        directory = os.getenv("KEYS_DIR", "/keys")
    
    vault_provider = get_vault_provider()
    
    logger.info(f"Starting SSH keys import from {directory}")
    logger.info(f"Using Vault provider: {vault_provider.__class__.__name__}")
    
    imported_keys = vault_provider.scan_ssh_keys_directory(directory)
    
    if not imported_keys:
        logger.warning("No SSH keys found or imported")
        return {
            "success": False,
            "message": "No keys found",
            "imported_keys": []
        }
    
    logger.info(f"Successfully imported {len(imported_keys)} SSH keys to Vault")
    
    # Выводим детальную информацию
    for key_info in imported_keys:
        logger.info(f"  ✓ {key_info['key_name']}")
        if key_info.get('metadata'):
            metadata = key_info['metadata']
            if metadata.get('server_name'):
                logger.info(f"    Server: {metadata['server_name']} ({metadata.get('server_host', 'N/A')})")
            if metadata.get('mcp_hub_hostname'):
                logger.info(f"    MCP Hub: {metadata['mcp_hub_hostname']}")
    
    return {
        "success": True,
        "message": f"Imported {len(imported_keys)} keys",
        "imported_keys": imported_keys
    }

def list_vault_keys() -> list[str]:
    """Выводит список всех SSH ключей в Vault"""
    vault_provider = get_vault_provider()
    keys = vault_provider.list_ssh_keys()
    
    logger.info(f"SSH keys in Vault ({len(keys)}):")
    for key_name in keys:
        metadata = vault_provider.get_ssh_key_metadata(key_name)
        logger.info(f"  • {key_name}")
        if metadata:
            if metadata.get('server_name'):
                logger.info(f"    Server: {metadata['server_name']}")
            if metadata.get('mcp_hub_hostname'):
                logger.info(f"    MCP Hub: {metadata['mcp_hub_hostname']}")
    
    return keys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_vault_keys()
        elif sys.argv[1] == "import":
            directory = sys.argv[2] if len(sys.argv) > 2 else None
            result = import_keys_from_directory(directory)
            if result["success"]:
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            print("Usage: python -m app.import_ssh_keys [import|list] [directory]")
            sys.exit(1)
    else:
        # По умолчанию импортируем
        result = import_keys_from_directory()
        sys.exit(0 if result["success"] else 1)
</content>