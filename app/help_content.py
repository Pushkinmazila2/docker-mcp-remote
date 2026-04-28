"""
Справочная информация для пользователей Docker MCP Hub
"""

HELP_TOPICS = {
    "overview": """
📚 DOCKER MCP HUB - OVERVIEW

Docker MCP Hub is a secure remote Docker management system with:
- 🔐 End-to-end encryption for passwords and SSH keys
- 👥 Multi-user support with custom roles
- 🔑 Bearer token-based authentication
- 💾 Multiple backup strategies
- 🏢 External vault support (HashiCorp Vault, AWS Secrets Manager)

Available help topics:
- backup: How to backup encrypted data
- create_user: How to create custom roles
- add_server: How to add remote Docker hosts
- external_vault: How to configure external key storage

Use get_help tool with topic parameter to get detailed instructions.
""",

    "backup": """
💾 HOW TO BACKUP ENCRYPTED DATA

═══════════════════════════════════════════════════════════════

📦 TWO TYPES OF BACKUPS:

1️⃣  ENCRYPTED DATA BACKUP (Recommended for regular backups)
   - Safe to store anywhere
   - Contains SSH keys, configs, roles (all encrypted)
   - Accessible by user and admin tokens
   - Cannot be decrypted without master keys

2️⃣  FULL BACKUP (Critical - admin only)
   - Contains master keys + encrypted data
   - Can decrypt everything
   - Store in extremely secure location

═══════════════════════════════════════════════════════════════

📋 STEP-BY-STEP: ENCRYPTED DATA BACKUP

1. Export encrypted backup:
   curl -H "Authorization: Bearer YOUR_TOKEN" \\
     http://localhost:8000/api/crypto/encrypted-backup > backup-$(date +%Y%m%d).json

2. Store the backup file securely:
   - Cloud storage (Dropbox, Google Drive, etc.)
   - Network backup system
   - External drive
   - Git repository (private)

3. Automate with cron (optional):
   0 2 * * * curl -H "Authorization: Bearer $TOKEN" \\
     http://localhost:8000/api/crypto/encrypted-backup > /backups/backup-$(date +%Y%m%d).json

═══════════════════════════════════════════════════════════════

🔄 HOW TO RESTORE:

1. Ensure master keys are in place (they should be if using same /data volume)

2. Restore encrypted data:
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d @backup.json \\
     http://localhost:8000/api/crypto/encrypted-restore

3. Verify restoration:
   curl -H "Authorization: Bearer YOUR_TOKEN" \\
     http://localhost:8000/api/servers

═══════════════════════════════════════════════════════════════

⚠️  IMPORTANT NOTES:

- Encrypted backups are SAFE to store - they cannot be decrypted without master keys
- Master keys are stored separately (in /data or external vault)
- For complete disaster recovery, you also need master keys backup (admin only)
- Test your backups regularly!

═══════════════════════════════════════════════════════════════
""",

    "create_user": """
👥 HOW TO CREATE CUSTOM USER ROLES

═══════════════════════════════════════════════════════════════

Custom roles allow you to create users with specific permissions.
Each role gets its own MCP endpoint and Bearer token.

═══════════════════════════════════════════════════════════════

📋 STEP-BY-STEP:

1. Prepare role configuration:
   {
     "username": "developer",
     "allowed_tools": [
       "list_servers",
       "list_containers",
       "view_logs",
       "read_file"
     ],
     "description": "Developer with read-only access"
   }

2. Create role via API (admin only):
   curl -X POST -H "Authorization: Bearer ADMIN_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{
       "username": "developer",
       "allowed_tools": ["list_servers", "list_containers", "view_logs"],
       "description": "Developer role"
     }' \\
     http://localhost:8000/api/roles

3. Save the returned token:
   {
     "username": "developer",
     "token": "generated-secure-token-here",
     "allowed_tools": [...],
     "created_at": "2026-04-28T10:00:00"
   }

4. User can now connect via MCP:
   Endpoint: /mcp/developer
   Token: Bearer generated-secure-token-here

═══════════════════════════════════════════════════════════════

🔧 AVAILABLE TOOLS:

Read-only:
- list_servers: List all configured servers
- list_containers: List containers on a server
- view_logs: View container logs
- read_file: Read files from containers

Write operations (use carefully):
- start_container: Start a container
- stop_container: Stop a container
- exec_command: Execute commands in containers
- add_server: Add new remote servers

═══════════════════════════════════════════════════════════════

📊 EXAMPLE ROLES:

Read-only developer:
  ["list_servers", "list_containers", "view_logs", "read_file"]

Ops engineer:
  ["list_servers", "list_containers", "start_container", "stop_container", "view_logs"]

Full access (like admin):
  ["list_servers", "list_containers", "start_container", "stop_container", 
   "add_server", "view_logs", "read_file", "exec_command"]

═══════════════════════════════════════════════════════════════

🔄 MANAGE ROLES:

List all roles:
  GET /api/roles

Update role permissions:
  PUT /api/roles/{username}

Regenerate token:
  POST /api/roles/{username}/regenerate-token

Delete role:
  DELETE /api/roles/{username}

═══════════════════════════════════════════════════════════════
""",

    "add_server": """
🖥️  HOW TO ADD REMOTE DOCKER HOST

═══════════════════════════════════════════════════════════════

Add remote servers to manage their Docker containers via MCP.
Supports password and SSH key authentication.

═══════════════════════════════════════════════════════════════

📋 METHOD 1: PASSWORD AUTHENTICATION (Recommended)

The system will automatically:
1. Generate SSH key pair
2. Connect with password
3. Install public key on remote host
4. Switch to key-based auth
5. Encrypt and store the key

Command:
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "production-server",
    "host": "192.168.1.100",
    "port": 22,
    "username": "ubuntu",
    "auth_type": "password",
    "password": "your-ssh-password",
    "description": "Production Docker host",
    "tags": ["prod", "web"]
  }' \\
  http://localhost:8000/api/servers

═══════════════════════════════════════════════════════════════

📋 METHOD 2: EXISTING SSH KEY

If you already have SSH key on the remote host:

curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "staging-server",
    "host": "staging.example.com",
    "port": 22,
    "username": "deploy",
    "auth_type": "key_path",
    "key_path": "/keys/existing_key",
    "description": "Staging environment"
  }' \\
  http://localhost:8000/api/servers

═══════════════════════════════════════════════════════════════

📋 METHOD 3: GENERATE KEY (Manual setup)

Generate key pair, then manually add public key to remote host:

curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "dev-server",
    "host": "dev.example.com",
    "port": 22,
    "username": "developer",
    "auth_type": "generate_key",
    "description": "Development server"
  }' \\
  http://localhost:8000/api/servers

Response will include public key to add to ~/.ssh/authorized_keys

═══════════════════════════════════════════════════════════════

✅ VERIFY CONNECTION:

1. List servers:
   curl -H "Authorization: Bearer YOUR_TOKEN" \\
     http://localhost:8000/api/servers

2. Test connection by listing containers:
   Use list_containers tool with the server_id

═══════════════════════════════════════════════════════════════

🔒 SECURITY NOTES:

- Passwords are encrypted with your Bearer token
- SSH keys are encrypted on disk
- Keys are decrypted only when needed
- Use password method for automatic setup
- Keys are never exposed in API responses

═══════════════════════════════════════════════════════════════

🗑️  REMOVE SERVER:

curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" \\
  http://localhost:8000/api/servers/{server_id}

═══════════════════════════════════════════════════════════════
""",

    "external_vault": """
🏢 HOW TO CONFIGURE EXTERNAL VAULT

═══════════════════════════════════════════════════════════════

Store master encryption keys in external vault instead of local files.
Supported: HashiCorp Vault, AWS Secrets Manager

═══════════════════════════════════════════════════════════════

🔐 OPTION 1: HASHICORP VAULT

1. Install hvac library:
   pip install hvac==2.1.0

2. Configure in docker_compose.yml:
   environment:
     VAULT_TYPE: "hashicorp"
     VAULT_ADDR: "https://vault.example.com:8200"
     VAULT_TOKEN: "your-vault-token"
     VAULT_SECRET_PATH: "secret/data/docker-mcp-hub"

3. Setup Vault:
   # Enable KV v2
   vault secrets enable -path=secret kv-v2
   
   # Create policy
   vault policy write docker-mcp-hub - <<EOF
   path "secret/data/docker-mcp-hub" {
     capabilities = ["create", "read", "update", "delete"]
   }
   EOF
   
   # Create token
   vault token create -policy=docker-mcp-hub

4. Restart container:
   docker-compose down && docker-compose up -d

5. Verify in logs:
   docker-compose logs | grep "Using HashiCorp Vault"

═══════════════════════════════════════════════════════════════

☁️  OPTION 2: AWS SECRETS MANAGER

1. Install boto3:
   pip install boto3==1.34.0

2. Configure in docker_compose.yml:
   environment:
     VAULT_TYPE: "aws"
     AWS_SECRET_NAME: "docker-mcp-hub/master-keys"
     AWS_REGION: "us-east-1"
     AWS_ACCESS_KEY_ID: "your-access-key"
     AWS_SECRET_ACCESS_KEY: "your-secret-key"

3. Create secret in AWS:
   aws secretsmanager create-secret \\
     --name docker-mcp-hub/master-keys \\
     --description "Master keys for Docker MCP Hub" \\
     --region us-east-1

4. Create IAM policy:
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": [
         "secretsmanager:GetSecretValue",
         "secretsmanager:PutSecretValue",
         "secretsmanager:CreateSecret",
         "secretsmanager:UpdateSecret"
       ],
       "Resource": "arn:aws:secretsmanager:*:*:secret:docker-mcp-hub/*"
     }]
   }

5. Restart container and verify

═══════════════════════════════════════════════════════════════

🔄 MIGRATION FROM LOCAL TO EXTERNAL VAULT:

1. Export master keys (admin only):
   curl -H "Authorization: Bearer ADMIN_TOKEN" \\
     http://localhost:8000/api/crypto/export > keys.json

2. Stop container:
   docker-compose down

3. Update docker_compose.yml with vault config

4. Start container:
   docker-compose up -d

5. Import keys:
   curl -X POST -H "Authorization: Bearer ADMIN_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d @keys.json \\
     http://localhost:8000/api/crypto/import

═══════════════════════════════════════════════════════════════

✅ BENEFITS OF EXTERNAL VAULT:

- 🔐 Keys never stored on disk
- 📊 Audit logs for all key access
- 🔄 Automatic key rotation
- 🏢 Centralized secrets management
- 💾 Built-in backup and HA
- 🔒 Better compliance (SOC2, HIPAA, etc.)

═══════════════════════════════════════════════════════════════

⚠️  IMPORTANT:

- Test vault connectivity before migration
- Keep backup of master keys during migration
- Verify vault access after restart
- Monitor vault logs for issues

═══════════════════════════════════════════════════════════════

For detailed documentation, see VAULT_SETUP.md
"""
}

def get_help(topic: str) -> str:
    """
    Получить справочную информацию по теме
    """
    return HELP_TOPICS.get(topic, f"Unknown topic: {topic}. Available topics: {', '.join(HELP_TOPICS.keys())}")