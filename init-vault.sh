#!/bin/bash

# Скрипт инициализации HashiCorp Vault для Docker MCP Hub

set -e

echo "🔐 Initializing HashiCorp Vault for Docker MCP Hub..."

# Ждем пока Vault запустится
echo "⏳ Waiting for Vault to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
  if curl -s http://localhost:8200/v1/sys/health > /dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  echo "   Attempt $attempt/$max_attempts..."
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "❌ Vault is not available after $max_attempts attempts"
  exit 1
fi

echo "✅ Vault is ready!"

# Устанавливаем переменные
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='root-token-change-me'

echo "📦 Enabling KV v2 secrets engine..."
vault secrets enable -path=secret kv-v2 2>/dev/null || echo "   KV v2 already enabled"

echo "📝 Creating policy for Docker MCP Hub..."
vault policy write docker-mcp-hub - <<EOF
# Master keys and salt
path "secret/data/docker-mcp-hub" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/docker-mcp-hub" {
  capabilities = ["list", "read"]
}

# Tokens storage
path "secret/data/docker-mcp-hub/tokens" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/docker-mcp-hub/tokens" {
  capabilities = ["list", "read"]
}

# SSH keys storage
path "secret/data/docker-mcp-hub/ssh-keys/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/docker-mcp-hub/ssh-keys/*" {
  capabilities = ["list", "read", "delete"]
}

path "secret/metadata/docker-mcp-hub/ssh-keys" {
  capabilities = ["list"]
}
EOF

echo "🔑 Creating token for Docker MCP Hub..."
TOKEN=$(vault token create -policy=docker-mcp-hub -ttl=0 -format=json | jq -r '.auth.client_token')

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Vault initialized successfully!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📋 Vault Configuration:"
echo "   Address: http://localhost:8200"
echo "   Token: $TOKEN"
echo "   Secret Path: secret/data/docker-mcp-hub"
echo ""
echo "🔐 Security:"
echo "   - Master keys stored in Vault"
echo "   - All tokens stored in Vault"
echo "   - SSH keys stored in Vault"
echo "   - Automatic token generation on first start"
echo "   - No sensitive data in container filesystem"
echo ""
echo "⚠️  IMPORTANT: Update docker_compose.yml with this token:"
echo ""
echo "   environment:"
echo "     VAULT_TOKEN: \"$TOKEN\""
echo ""
echo "   Or use root token (DEV ONLY - NOT FOR PRODUCTION):"
echo "     VAULT_TOKEN: \"root-token-change-me\""
echo ""
echo "📝 Next steps:"
echo "   1. Update VAULT_TOKEN in docker_compose.yml"
echo "   2. Run: docker compose up -d"
echo "   3. Check logs: docker compose logs -f mcp-hub"
echo "   4. Access tokens will be displayed in mcp-hub logs"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
