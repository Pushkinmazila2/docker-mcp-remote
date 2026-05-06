# Changelog: Vault-Only SSH Keys Storage

## Version 2.0.0 - Vault-Only Storage

### 🔐 Major Changes

#### 1. SSH Keys Storage
- **BREAKING**: All SSH keys now stored exclusively in HashiCorp Vault
- Removed local file storage for SSH keys
- Automatic key discovery and import from `/keys` directory on startup
- Keys are only temporarily written to disk during SSH operations

#### 2. Server Configuration Storage
- Server configurations (`servers.json`) now stored in Vault
- Local file storage kept as fallback for compatibility
- Automatic migration from local to Vault storage

#### 3. MCP Hub Identification
- All generated SSH keys include `mcp_hub@{hostname}` comment
- Keys installed on remote servers are tagged with MCP Hub hostname
- Easy identification and management of keys across multiple servers

#### 4. Metadata Support
- Each SSH key can have associated metadata in Vault:
  - `server_id`: Server identifier
  - `server_name`: Human-readable server name
  - `server_host`: Server hostname/IP
  - `created_at`: Creation timestamp
  - `mcp_hub_hostname`: MCP Hub instance identifier
  - `description`: Optional description

#### 5. Automatic Import Utility
- New `import_ssh_keys.py` module for key management
- Scans directories and imports keys with metadata
- Supports `config.json` for bulk metadata import

### 📝 API Changes

#### VaultProvider Interface
New methods added to all Vault providers:
```python
- get_ssh_key_metadata(key_name: str) -> Optional[dict]
- set_ssh_key_metadata(key_name: str, metadata: dict) -> bool
- scan_ssh_keys_directory(directory: str) -> list[dict]
- get_servers_config() -> Optional[dict]
- set_servers_config(config: dict) -> bool
```

#### Server Manager
- `_load()`: Now loads from Vault first, local file as fallback
- `_save()`: Saves to both Vault and local file
- `add_server()`: Keys saved directly to Vault, no local storage
- `remove_server()`: Removes keys from Vault only

#### SSH Client
- `ssh_connect()`: Retrieves keys from Vault only
- No fallback to local encrypted files
- Better error messages when keys not found

### 🚀 New Features

1. **Automatic Key Import**
   - On container startup, scans `/keys` directory
   - Imports all SSH keys to Vault
   - Reads metadata from `config.json` if present
   - Logs detailed import information

2. **Key Management CLI**
   ```bash
   # List keys in Vault
   python -m app.import_ssh_keys list
   
   # Import keys from directory
   python -m app.import_ssh_keys import /path/to/keys
   ```

3. **Enhanced Security**
   - No sensitive data in container filesystem
   - All keys encrypted at rest in Vault
   - Vault audit logging support
   - Better access control via Vault policies

4. **Better Identification**
   - SSH keys tagged with MCP Hub hostname
   - Easy to identify which keys belong to which instance
   - Simplifies multi-instance deployments

### 🔧 Configuration Changes

#### Environment Variables
```yaml
# New/Updated
VAULT_TYPE: "hashicorp"  # Required, no longer optional
KEYS_DIR: "/keys"        # Now only for initial import

# Behavior Changes
DATA_DIR: "/data"         # Now fallback only for servers.json
```

#### Docker Compose
```yaml
volumes:
  - ./keys:/keys          # Only for initial import, not runtime
  - ./data:/data          # Fallback only
```

### 📚 Documentation

New documentation files:
- `docs/SSH_KEYS_VAULT.md` - Complete guide to Vault-based key storage
- `docs/MIGRATION_GUIDE.md` - Step-by-step migration instructions
- `docs/VAULT_SSH_KEYS_README.md` - Quick start and operations guide
- `docs/ssh-keys-config.example.json` - Example metadata configuration

### ⚠️ Breaking Changes

1. **Local SSH Key Storage Removed**
   - Keys in `/keys` directory are no longer used at runtime
   - Only imported to Vault on startup
   - Must use Vault for all key operations

2. **Vault Required**
   - `VAULT_TYPE=local` no longer supports SSH keys
   - HashiCorp Vault or AWS Secrets Manager required
   - System will not start without valid Vault connection

3. **Key Path Format Changed**
   - Server configs now store key name only, not full path
   - Old: `key_path: "/keys/key_abc123"`
   - New: `generated_key_name: "key_abc123"`

### 🔄 Migration Path

#### Automatic Migration
1. Place existing keys in `/keys` directory
2. Optionally create `config.json` with metadata
3. Start container - keys automatically imported
4. Verify with `python -m app.import_ssh_keys list`

#### Manual Migration
```bash
# Export from old system
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/crypto/full-backup > backup.json

# Import to new system
docker exec docker-mcp-hub python -m app.import_ssh_keys import /keys
```

See `docs/MIGRATION_GUIDE.md` for detailed instructions.

### 🐛 Bug Fixes

- Fixed race condition in key file cleanup
- Improved error handling for Vault connection failures
- Better logging for key import operations
- Fixed permission issues with temporary key files

### 🔒 Security Improvements

1. **No Local Key Storage**
   - Eliminates risk of keys in container filesystem
   - Reduces attack surface
   - Better compliance with security policies

2. **Vault Audit Logging**
   - All key access logged in Vault
   - Better audit trail
   - Easier compliance reporting

3. **Key Identification**
   - MCP Hub hostname in key comments
   - Easier to track key usage
   - Simplifies key rotation

4. **Metadata Tracking**
   - Server information stored with keys
   - Better key lifecycle management
   - Easier cleanup of unused keys

### 📊 Performance

- Slightly slower first connection (Vault lookup)
- Faster subsequent connections (no decryption needed)
- Reduced disk I/O (no local key files)
- Better scalability with multiple instances

### 🧪 Testing

New test scenarios:
- Key import from directory
- Metadata preservation
- Vault connection failures
- Key not found errors
- Multi-instance key identification

### 📦 Dependencies

No new dependencies required. Existing:
- `hvac` for HashiCorp Vault (optional)
- `boto3` for AWS Secrets Manager (optional)

### 🔮 Future Enhancements

- [ ] Web UI for key management
- [ ] Automatic key rotation
- [ ] Key expiration policies
- [ ] Multi-region Vault support
- [ ] Key usage analytics
- [ ] Automated key deployment

### 📞 Support

For issues or questions:
1. Check documentation in `docs/`
2. Review migration guide
3. Check container logs
4. Create GitHub issue with details

### 🙏 Acknowledgments

Thanks to all contributors and users who provided feedback on the security improvements.

---

## Upgrade Instructions

### From v1.x to v2.0

1. **Backup your data**
   ```bash
   tar -czf backup.tar.gz ./keys ./data
   ```

2. **Update docker-compose.yml**
   - Ensure Vault is configured
   - Update environment variables

3. **Start new version**
   ```bash
   docker compose pull
   docker compose up -d
   ```

4. **Verify migration**
   ```bash
   docker logs docker-mcp-hub | grep -i import
   docker exec docker-mcp-hub python -m app.import_ssh_keys list
   ```

5. **Test connectivity**
   - List servers
   - Connect to a server
   - Verify key-based auth works

### Rollback Procedure

If needed, rollback to v1.x:

```bash
# Stop containers
docker compose down

# Restore backup
tar -xzf backup.tar.gz

# Use old version
git checkout v1.x
docker compose up -d
```

---

**Full documentation**: See `docs/` directory for complete guides and examples.
</contents>