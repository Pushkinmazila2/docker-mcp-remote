# Migration Guide: Vault-Only SSH Keys Storage

## Overview

This guide helps you migrate from the old system (local SSH keys storage) to the new Vault-only storage system.

## What Changed?

### Before (Old System)
- SSH keys stored in `/keys` directory as encrypted files
- Server configs in `/data/servers.json`
- Mixed storage: some in Vault, some local

### After (New System)
- **All SSH keys stored exclusively in Vault**
- Server configs stored in Vault (with local fallback)
- Automatic key discovery and import from `/keys` directory
- SSH keys include MCP Hub identification
- Metadata support for keys

## Migration Steps

### Step 1: Backup Your Data

Before migrating, backup your existing data:

```bash
# Backup SSH keys
tar -czf ssh-keys-backup.tar.gz /path/to/keys/

# Backup server configs
cp /path/to/data/servers.json servers-backup.json

# Export from old system (if using API)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/crypto/full-backup > full-backup.json
```

### Step 2: Prepare Keys Directory

If you have existing SSH keys, organize them:

```bash
# Your keys directory should look like:
/keys/
  ├── config.json          # Optional: metadata
  ├── key_abc123           # Private key
  ├── key_abc123.pub       # Public key
  ├── key_def456
  └── key_def456.pub
```

### Step 3: Create Metadata File (Optional)

Create `/keys/config.json` to preserve server information:

```json
{
  "keys": {
    "key_abc123": {
      "server_id": "abc123",
      "server_name": "Production Server",
      "server_host": "prod.example.com",
      "created_at": "2024-01-01T00:00:00Z",
      "mcp_hub_hostname": "docker-mcp-hub",
      "description": "Main production server"
    }
  }
}
```

### Step 4: Update Docker Compose

Ensure your `docker-compose.yml` has Vault configured:

```yaml
services:
  vault:
    image: hashicorp/vault:1.15
    container_name: docker-mcp-vault
    # ... vault configuration ...

  mcp-hub:
    depends_on:
      vault:
        condition: service_healthy
    environment:
      VAULT_TYPE: "hashicorp"
      VAULT_ADDR: "http://vault:8200"
      VAULT_TOKEN: "your-vault-token"
      VAULT_SECRET_PATH: "secret/data/docker-mcp-hub"
      KEYS_DIR: "/keys"
    volumes:
      - ./keys:/keys  # Mount for initial import only
```

### Step 5: Initialize Vault

Run the Vault initialization script:

```bash
# Start Vault
docker compose up -d vault

# Wait for Vault to be ready
sleep 10

# Initialize Vault
docker exec docker-mcp-vault sh -c '
  export VAULT_ADDR=http://localhost:8200
  export VAULT_TOKEN=root-token-change-me
  vault secrets enable -path=secret kv-v2
'

# Or use the init script
./init-vault.sh
```

### Step 6: Start MCP Hub

Start the MCP Hub container:

```bash
docker compose up -d mcp-hub
```

The container will automatically:
1. Connect to Vault
2. Scan `/keys` directory
3. Import all SSH keys to Vault
4. Import metadata from `config.json`
5. Clean up (keys remain in `/keys` but are not used)

### Step 7: Verify Migration

Check that keys were imported:

```bash
# List keys in Vault
docker exec docker-mcp-hub python -m app.import_ssh_keys list

# Check logs
docker logs docker-mcp-hub | grep -i "import"
```

Expected output:
```
🔑 Importing SSH keys from /keys to Vault...
Loaded metadata for 2 keys from config.json
Imported SSH key key_abc123 to Vault
Imported SSH key key_def456 to Vault
Successfully imported 2 SSH keys to Vault
  ✓ key_abc123
    Server: Production Server (prod.example.com)
    MCP Hub: docker-mcp-hub
  ✓ key_def456
    Server: Staging Server (staging.example.com)
    MCP Hub: docker-mcp-hub
```

### Step 8: Test Connectivity

Test that servers are accessible:

```bash
# Via API
curl -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_servers"}}' \
  http://localhost:8000/mcp/user

# Test connection to a server
curl -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_containers","arguments":{"server_id":"abc123"}}}' \
  http://localhost:8000/mcp/user
```

### Step 9: Clean Up (Optional)

After verifying everything works:

```bash
# Keys are now in Vault, you can remove local copies
# But keep them as backup for a while
mv /path/to/keys /path/to/keys.backup

# Or just remove the mount from docker-compose.yml
# The /keys directory is only needed for initial import
```

## Rollback Procedure

If you need to rollback:

### Option 1: Use Local Storage

```yaml
# In docker-compose.yml
environment:
  VAULT_TYPE: "local"  # Switch back to local storage
```

Restore your backups:
```bash
tar -xzf ssh-keys-backup.tar.gz -C /path/to/
cp servers-backup.json /path/to/data/servers.json
```

### Option 2: Export from Vault

```bash
# Export keys from Vault back to files
docker exec docker-mcp-hub python -c "
import os
from app.vault_providers import get_vault_provider
from pathlib import Path

vault = get_vault_provider()
keys_dir = Path('/keys')
keys_dir.mkdir(exist_ok=True)

for key_name in vault.list_ssh_keys():
    private_key = vault.get_ssh_key(key_name)
    if private_key:
        (keys_dir / key_name).write_text(private_key)
        print(f'Exported {key_name}')
"
```

## Troubleshooting

### Keys Not Imported

**Problem**: Keys in `/keys` directory but not in Vault

**Solution**:
```bash
# Manual import
docker exec docker-mcp-hub python -m app.import_ssh_keys import /keys

# Check permissions
ls -la /path/to/keys/
# Private keys should be 600, public keys 644
```

### Vault Connection Failed

**Problem**: Cannot connect to Vault

**Solution**:
```bash
# Check Vault status
docker ps | grep vault
docker logs docker-mcp-vault

# Verify environment variables
docker exec docker-mcp-hub env | grep VAULT

# Test Vault connection
docker exec docker-mcp-hub curl -s $VAULT_ADDR/v1/sys/health
```

### SSH Connection Failed

**Problem**: Cannot connect to servers after migration

**Solution**:
```bash
# Verify key exists in Vault
docker exec docker-mcp-hub python -m app.import_ssh_keys list

# Check server config
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/servers

# Test SSH manually
docker exec docker-mcp-hub python -c "
from app.vault_providers import get_vault_provider
vault = get_vault_provider()
key = vault.get_ssh_key('key_abc123')
print('Key found' if key else 'Key not found')
"
```

### Metadata Not Preserved

**Problem**: Server information lost after migration

**Solution**:
```bash
# Manually set metadata
docker exec docker-mcp-hub python -c "
from app.vault_providers import get_vault_provider
import json

vault = get_vault_provider()
metadata = {
    'server_id': 'abc123',
    'server_name': 'Production Server',
    'server_host': 'prod.example.com',
    'mcp_hub_hostname': 'docker-mcp-hub'
}
vault.set_ssh_key_metadata('key_abc123', metadata)
print('Metadata saved')
"
```

## Post-Migration Checklist

- [ ] All SSH keys imported to Vault
- [ ] Server configs accessible
- [ ] Can list servers via API
- [ ] Can connect to servers and list containers
- [ ] Metadata preserved for all keys
- [ ] Backups created and verified
- [ ] Documentation updated
- [ ] Team notified of changes
- [ ] Old local keys backed up
- [ ] Monitoring configured for Vault

## Benefits After Migration

✅ **Security**
- All secrets in one secure location
- No sensitive data in container filesystem
- Vault audit logging enabled
- Better access control

✅ **Management**
- Centralized key management
- Easy key rotation
- Metadata tracking
- MCP Hub identification on remote servers

✅ **Reliability**
- Automatic key discovery
- Consistent storage
- Better error handling
- Fallback mechanisms

## Support

If you encounter issues during migration:

1. Check the logs: `docker logs docker-mcp-hub`
2. Review the documentation: `docs/SSH_KEYS_VAULT.md`
3. Use the troubleshooting section above
4. Create an issue on GitHub with:
   - Migration step where you encountered the issue
   - Error messages from logs
   - Your docker-compose.yml (redact sensitive data)
   - Output of `docker ps` and `docker logs`
</contents>