# SSH Keys Management in Vault

## Overview

Starting from this version, **all SSH keys are stored exclusively in Vault**. Local file storage for SSH keys has been removed to improve security and centralize secrets management.

## Key Features

### 1. Vault-Only Storage
- All SSH private keys are stored in Vault
- No local file storage for keys (except temporary files during operations)
- Automatic cleanup of temporary key files after use

### 2. Automatic Key Discovery
When the container starts, it automatically scans the `/keys` directory and imports any SSH keys found into Vault. This allows for easy migration from local storage.

### 3. Metadata Support
Each SSH key can have associated metadata stored in Vault:
- `server_id`: ID of the server this key belongs to
- `server_name`: Human-readable server name
- `server_host`: Server hostname/IP
- `created_at`: Timestamp when the key was created
- `mcp_hub_hostname`: Hostname of the MCP Hub container that created the key
- `description`: Optional description

### 4. MCP Hub Identification
When SSH keys are installed on remote servers, they include a comment identifying the MCP Hub container:
```
ssh-ed25519 AAAAC3... mcp_hub@docker-mcp-hub
```

This makes it easy to identify which keys were installed by which MCP Hub instance.

## Directory Structure

### Keys Directory (`/keys`)
```
/keys/
  ├── config.json          # Optional: metadata for existing keys
  ├── key_abc123           # Private key (will be imported to Vault)
  ├── key_abc123.pub       # Public key
  ├── key_def456
  └── key_def456.pub
```

### Vault Structure
```
secret/data/docker-mcp-hub/
  ├── master_key           # Master encryption key
  ├── salt                 # Encryption salt
  ├── tokens               # Access tokens
  ├── servers              # Server configurations (moved from /data/servers.json)
  └── ssh-keys/
      ├── key_abc123       # Private key + public key + metadata
      └── key_def456
```

## Configuration File Format

Place a `config.json` file in your `/keys` directory to provide metadata for existing keys:

```json
{
  "keys": {
    "key_abc123": {
      "server_id": "abc123",
      "server_name": "Production Server",
      "server_host": "prod.example.com",
      "created_at": "2024-01-01T00:00:00Z",
      "mcp_hub_hostname": "docker-mcp-hub",
      "description": "SSH key for production server access"
    }
  }
}
```

See `docs/ssh-keys-config.example.json` for a complete example.

## Migration from Local Storage

If you have existing SSH keys in local storage:

1. **Automatic Migration**: Place your keys in `/keys` directory and restart the container. They will be automatically imported to Vault.

2. **Manual Import**: Use the import utility:
   ```bash
   docker exec docker-mcp-hub python -m app.import_ssh_keys import /keys
   ```

3. **Verify Import**: List keys in Vault:
   ```bash
   docker exec docker-mcp-hub python -m app.import_ssh_keys list
   ```

## Operations

### List Keys in Vault
```bash
docker exec docker-mcp-hub python -m app.import_ssh_keys list
```

### Import Keys from Directory
```bash
docker exec docker-mcp-hub python -m app.import_ssh_keys import /path/to/keys
```

### Add Server with Key Generation
When you add a server with `auth_type: "generate_key"` or `auth_type: "password"` (with auto-key-install), the key is:
1. Generated with MCP Hub identification comment
2. Saved directly to Vault
3. Metadata is automatically created
4. Local temporary files are cleaned up

### Key Installation on Remote Servers
When installing keys on remote servers (password auth with auto-install), the public key is added to `~/.ssh/authorized_keys` with the MCP Hub identifier:

```bash
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... mcp_hub@docker-mcp-hub
```

This allows you to easily identify and manage keys installed by MCP Hub.

## Security Benefits

1. **Centralized Storage**: All secrets in one secure location
2. **No Local Files**: Reduced attack surface
3. **Audit Trail**: Vault provides audit logging
4. **Access Control**: Vault's policy system controls access
5. **Encryption at Rest**: Vault encrypts all data
6. **Key Rotation**: Easy to rotate keys through Vault
7. **Identification**: Keys are tagged with MCP Hub hostname

## Environment Variables

```bash
# Vault Configuration
VAULT_TYPE=hashicorp              # Use HashiCorp Vault
VAULT_ADDR=http://vault:8200      # Vault address
VAULT_TOKEN=your-vault-token      # Vault access token
VAULT_SECRET_PATH=secret/data/docker-mcp-hub  # Base path in Vault

# Keys Directory (for import only)
KEYS_DIR=/keys                    # Directory to scan for keys on startup
```

## Troubleshooting

### Keys Not Found
If you get "SSH key not found in Vault" errors:
1. Check if keys were imported: `docker exec docker-mcp-hub python -m app.import_ssh_keys list`
2. Verify Vault connection: Check container logs
3. Re-import keys: `docker exec docker-mcp-hub python -m app.import_ssh_keys import /keys`

### Vault Connection Issues
If Vault is unavailable:
1. Check Vault container status: `docker ps | grep vault`
2. Check Vault logs: `docker logs docker-mcp-vault`
3. Verify VAULT_ADDR and VAULT_TOKEN in docker-compose.yml

### Migration Issues
If automatic migration fails:
1. Check container logs for import errors
2. Verify `/keys` directory is mounted correctly
3. Ensure keys have correct permissions (600 for private, 644 for public)
4. Try manual import with verbose logging

## Best Practices

1. **Always use Vault**: Don't store keys locally in production
2. **Use config.json**: Provide metadata for better key management
3. **Regular Backups**: Backup Vault data regularly
4. **Key Rotation**: Rotate SSH keys periodically
5. **Monitor Access**: Use Vault audit logs to monitor key access
6. **Unique Identifiers**: Each MCP Hub instance should have a unique hostname
7. **Clean Up**: Remove old keys from remote servers when decommissioning MCP Hub instances

## API Changes

### Server Configuration
Server configurations are now stored in Vault instead of `/data/servers.json`:
- Primary storage: `secret/data/docker-mcp-hub/servers`
- Fallback: `/data/servers.json` (for compatibility)

### SSH Key References
Server configs now reference keys by name only (not full path):
```json
{
  "id": "abc123",
  "generated_key_name": "key_abc123",  // Just the name
  "key_path": "key_abc123"              // Not /keys/key_abc123
}
```

## Future Enhancements

- [ ] Web UI for key management
- [ ] Key expiration and automatic rotation
- [ ] Multi-region Vault support
- [ ] Key usage analytics
- [ ] Automated key deployment to new servers
</contents>"