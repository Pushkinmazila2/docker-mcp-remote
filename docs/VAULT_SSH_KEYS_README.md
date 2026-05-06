# Vault-Based SSH Keys Storage

## Quick Start

### 1. Start the System

```bash
# Start Vault and MCP Hub
docker compose up -d

# Check logs
docker logs -f docker-mcp-hub
```

### 2. Automatic Key Import

On first start, the system automatically:
- Scans `/keys` directory for SSH keys
- Imports them to Vault with metadata
- Identifies keys with `mcp_hub@hostname` comment

### 3. Add a New Server

#### Option A: Generate Key Automatically

```bash
curl -X POST http://localhost:8000/api/servers \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Server",
    "host": "prod.example.com",
    "username": "deploy",
    "auth_type": "generate_key",
    "description": "Main production server"
  }'
```

The system will:
1. Generate SSH key pair with `mcp_hub@docker-mcp-hub` comment
2. Store private key in Vault
3. Return public key for you to add to server

#### Option B: Auto-Install Key via Password

```bash
curl -X POST http://localhost:8000/api/servers \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Staging Server",
    "host": "staging.example.com",
    "username": "deploy",
    "auth_type": "password",
    "password": "temporary-password",
    "description": "Staging environment"
  }'
```

The system will:
1. Generate SSH key pair
2. Connect via password
3. Install public key to `~/.ssh/authorized_keys` with `mcp_hub@docker-mcp-hub` comment
4. Store private key in Vault
5. Switch to key-based auth

## Key Features

### 🔐 Vault-Only Storage

- **All SSH keys stored exclusively in Vault**
- No local file storage (except temporary during operations)
- Automatic cleanup of temporary files
- Encrypted at rest in Vault

### 🔍 Automatic Discovery

```bash
# Keys in /keys directory are automatically imported on startup
/keys/
  ├── config.json          # Optional metadata
  ├── key_abc123           # Will be imported to Vault
  ├── key_abc123.pub
  ├── key_def456
  └── key_def456.pub
```

### 🏷️ MCP Hub Identification

All generated keys include identification:

```bash
# On remote server's ~/.ssh/authorized_keys:
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... mcp_hub@docker-mcp-hub
```

Benefits:
- Easy to identify which keys belong to which MCP Hub instance
- Simplifies key management across multiple servers
- Helps with auditing and cleanup

### 📊 Metadata Support

Each key can have metadata:

```json
{
  "server_id": "abc123",
  "server_name": "Production Server",
  "server_host": "prod.example.com",
  "created_at": "2024-01-01T00:00:00Z",
  "mcp_hub_hostname": "docker-mcp-hub",
  "description": "Main production server"
}
```

## Configuration

### Environment Variables

```yaml
environment:
  # Vault Configuration (REQUIRED)
  VAULT_TYPE: "hashicorp"              # hashicorp | aws | local
  VAULT_ADDR: "http://vault:8200"      # Vault server address
  VAULT_TOKEN: "your-vault-token"      # Vault access token
  VAULT_SECRET_PATH: "secret/data/docker-mcp-hub"  # Base path
  
  # Directories
  DATA_DIR: /data                      # Fallback for server configs
  KEYS_DIR: /keys                      # For initial import only
```

### Vault Structure

```
secret/data/docker-mcp-hub/
├── master_key                    # Master encryption key
├── salt                          # Encryption salt
├── tokens                        # Access tokens
├── servers                       # Server configurations
└── ssh-keys/
    ├── key_abc123/
    │   ├── private_key          # Private SSH key
    │   ├── public_key           # Public SSH key
    │   └── metadata             # Key metadata
    └── key_def456/
        ├── private_key
        ├── public_key
        └── metadata
```

## Operations

### List Keys in Vault

```bash
docker exec docker-mcp-hub python -m app.import_ssh_keys list
```

Output:
```
SSH keys in Vault (2):
  • key_abc123
    Server: Production Server
    MCP Hub: docker-mcp-hub
  • key_def456
    Server: Staging Server
    MCP Hub: docker-mcp-hub
```

### Import Keys from Directory

```bash
# Import from custom directory
docker exec docker-mcp-hub python -m app.import_ssh_keys import /path/to/keys

# Import from default KEYS_DIR
docker exec docker-mcp-hub python -m app.import_ssh_keys import
```

### View Key Metadata

```bash
docker exec docker-mcp-hub python -c "
from app.vault_providers import get_vault_provider
import json

vault = get_vault_provider()
metadata = vault.get_ssh_key_metadata('key_abc123')
print(json.dumps(metadata, indent=2))
"
```

### Update Key Metadata

```bash
docker exec docker-mcp-hub python -c "
from app.vault_providers import get_vault_provider

vault = get_vault_provider()
metadata = {
    'server_id': 'abc123',
    'server_name': 'Updated Server Name',
    'server_host': 'new-host.example.com',
    'mcp_hub_hostname': 'docker-mcp-hub',
    'description': 'Updated description'
}
vault.set_ssh_key_metadata('key_abc123', metadata)
print('Metadata updated')
"
```

### Export Keys (Backup)

```bash
# Export all keys from Vault to local directory
docker exec docker-mcp-hub python -c "
import os
from app.vault_providers import get_vault_provider
from pathlib import Path

vault = get_vault_provider()
backup_dir = Path('/tmp/keys-backup')
backup_dir.mkdir(exist_ok=True)

for key_name in vault.list_ssh_keys():
    private_key = vault.get_ssh_key(key_name)
    if private_key:
        (backup_dir / key_name).write_text(private_key)
        print(f'Exported {key_name}')
"

# Copy from container
docker cp docker-mcp-hub:/tmp/keys-backup ./keys-backup
```

## Security Best Practices

### 1. Use Production Vault Token

```bash
# Don't use dev root token in production
# Generate a proper token with limited permissions
vault token create -policy=docker-mcp-hub -ttl=0
```

### 2. Enable Vault Audit Logging

```bash
vault audit enable file file_path=/vault/logs/audit.log
```

### 3. Regular Backups

```bash
# Backup Vault data
docker exec docker-mcp-vault vault operator raft snapshot save /vault/data/backup.snap

# Copy backup
docker cp docker-mcp-vault:/vault/data/backup.snap ./vault-backup.snap
```

### 4. Key Rotation

```bash
# Generate new key for server
curl -X POST http://localhost:8000/api/servers \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{...}'

# Remove old key from remote server
ssh user@server "sed -i '/mcp_hub@old-hostname/d' ~/.ssh/authorized_keys"

# Delete old key from Vault
curl -X DELETE http://localhost:8000/api/servers/old-server-id \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 5. Monitor Key Usage

```bash
# Check Vault audit logs
docker exec docker-mcp-vault cat /vault/logs/audit.log | \
  grep "ssh-keys" | \
  jq '.request.path'
```

## Troubleshooting

### Keys Not Found

```bash
# Check if keys are in Vault
docker exec docker-mcp-hub python -m app.import_ssh_keys list

# Re-import if needed
docker exec docker-mcp-hub python -m app.import_ssh_keys import /keys
```

### Vault Connection Issues

```bash
# Check Vault status
docker ps | grep vault
docker logs docker-mcp-vault

# Test connection
docker exec docker-mcp-hub curl -s $VAULT_ADDR/v1/sys/health

# Verify token
docker exec docker-mcp-hub curl -s \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  $VAULT_ADDR/v1/auth/token/lookup-self
```

### SSH Connection Failed

```bash
# Verify key exists
docker exec docker-mcp-hub python -c "
from app.vault_providers import get_vault_provider
vault = get_vault_provider()
key = vault.get_ssh_key('key_abc123')
print('Found' if key else 'Not found')
"

# Check server config
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/servers | jq

# Test SSH manually
docker exec docker-mcp-hub ssh -i /tmp/test-key user@host
```

## Migration from Local Storage

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for detailed migration instructions.

Quick migration:

```bash
# 1. Backup existing keys
tar -czf keys-backup.tar.gz ./keys/

# 2. Start new system
docker compose up -d

# 3. Keys are automatically imported
# Check logs to verify
docker logs docker-mcp-hub | grep -i import

# 4. Verify
docker exec docker-mcp-hub python -m app.import_ssh_keys list
```

## Advanced Usage

### Custom Vault Provider

To use AWS Secrets Manager instead:

```yaml
environment:
  VAULT_TYPE: "aws"
  AWS_SECRET_NAME: "docker-mcp-hub/master-keys"
  AWS_REGION: "us-east-1"
  AWS_ACCESS_KEY_ID: "your-key"
  AWS_SECRET_ACCESS_KEY: "your-secret"
```

### Multiple MCP Hub Instances

Each instance should have unique hostname:

```yaml
services:
  mcp-hub-prod:
    hostname: mcp-hub-prod
    # Keys will be tagged as mcp_hub@mcp-hub-prod
  
  mcp-hub-staging:
    hostname: mcp-hub-staging
    # Keys will be tagged as mcp_hub@mcp-hub-staging
```

### Programmatic Key Management

```python
from app.vault_providers import get_vault_provider

vault = get_vault_provider()

# List all keys
keys = vault.list_ssh_keys()

# Get key with metadata
for key_name in keys:
    private_key = vault.get_ssh_key(key_name)
    metadata = vault.get_ssh_key_metadata(key_name)
    print(f"{key_name}: {metadata.get('server_name')}")

# Add new key
vault.set_ssh_key('new_key', private_key_content, public_key_content)
vault.set_ssh_key_metadata('new_key', {
    'server_name': 'New Server',
    'mcp_hub_hostname': 'docker-mcp-hub'
})
```

## FAQ

**Q: Can I still use local file storage?**
A: Not recommended. Set `VAULT_TYPE=local` only for testing. SSH keys will not be stored locally.

**Q: What happens if Vault is unavailable?**
A: The system will fail to start. Vault is required for SSH key storage.

**Q: How do I rotate keys?**
A: Generate a new key, add it to the server, test connectivity, then remove the old key.

**Q: Can I use existing SSH keys?**
A: Yes, place them in `/keys` directory and they'll be imported on startup.

**Q: How do I backup keys?**
A: Backup Vault data or use the export script above. Also backup `/data/servers.json`.

**Q: What's the `mcp_hub@hostname` comment for?**
A: It identifies which MCP Hub instance installed the key, making management easier.

## Resources

- [Full Documentation](./SSH_KEYS_VAULT.md)
- [Migration Guide](./MIGRATION_GUIDE.md)
- [Vault Documentation](https://www.vaultproject.io/docs)
- [SSH Key Management Best Practices](https://www.ssh.com/academy/ssh/key-management)
</contents>