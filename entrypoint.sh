#!/bin/bash
set -e

echo "🚀 Starting Docker MCP Hub..."

# Функция для проверки доступности Vault
wait_for_vault() {
    if [ "$VAULT_TYPE" != "hashicorp" ]; then
        return 0
    fi
    
    echo "⏳ Waiting for Vault to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "${VAULT_ADDR}/v1/sys/health" > /dev/null 2>&1; then
            echo "✅ Vault is ready!"
            return 0
        fi
        attempt=$((attempt + 1))
        echo "   Attempt $attempt/$max_attempts..."
        sleep 2
    done
    
    echo "❌ Vault is not available after $max_attempts attempts"
    echo "⚠️  Falling back to local storage"
    export VAULT_TYPE="local"
}

# Функция для инициализации Vault
init_vault() {
    if [ "$VAULT_TYPE" != "hashicorp" ]; then
        return 0
    fi
    
    echo "🔐 Initializing Vault connection..."
    
    # Проверяем доступность Vault
    if ! curl -s -f "${VAULT_ADDR}/v1/sys/health" > /dev/null 2>&1; then
        echo "❌ Cannot connect to Vault at ${VAULT_ADDR}"
        echo "⚠️  Falling back to local storage"
        export VAULT_TYPE="local"
        return 1
    fi
    
    # Проверяем токен
    if ! curl -s -f -H "X-Vault-Token: ${VAULT_TOKEN}" "${VAULT_ADDR}/v1/auth/token/lookup-self" > /dev/null 2>&1; then
        echo "❌ Invalid Vault token"
        echo "⚠️  Falling back to local storage"
        export VAULT_TYPE="local"
        return 1
    fi
    
    echo "✅ Vault connection successful"
    
    # Выводим информацию о Vault
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "🔐 VAULT CONFIGURATION"
    echo "═══════════════════════════════════════════════════════════════"
    echo "   Type: HashiCorp Vault"
    echo "   Address: ${VAULT_ADDR}"
    echo "   Secret Path: ${VAULT_SECRET_PATH}"
    echo "   Status: Connected ✅"
    echo ""
    echo "📦 Vault Storage:"
    echo "   - Master encryption keys"
    echo "   - Access tokens (USER, ADMIN, WEB_UI)"
    echo "   - Custom role tokens"
    echo "   - SSH private keys"
    echo "   - Server passwords (encrypted)"
    echo ""
    echo "🔒 Security: All sensitive data stored in Vault"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
}

# Ждем Vault если используется
wait_for_vault

# Инициализируем Vault
init_vault

# Импортируем SSH ключи из директории в Vault (если есть)
import_ssh_keys() {
    if [ "$VAULT_TYPE" = "local" ]; then
        echo "⚠️  Skipping SSH keys import (local storage mode)"
        return 0
    fi
    
    if [ -d "$KEYS_DIR" ] && [ "$(ls -A $KEYS_DIR 2>/dev/null)" ]; then
        echo "🔑 Importing SSH keys from $KEYS_DIR to Vault..."
        python -m app.import_ssh_keys import "$KEYS_DIR" || {
            echo "⚠️  Failed to import SSH keys, continuing anyway..."
        }
    else
        echo "ℹ️  No SSH keys found in $KEYS_DIR"
    fi
}

# Импортируем ключи
import_ssh_keys

# Запускаем приложение
echo "🎯 Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
EOF
chmod +x entrypoint.sh
</contents>