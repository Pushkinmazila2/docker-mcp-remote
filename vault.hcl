ui = true

storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true  # В продакшене замените на tls_cert_file/tls_key_file
}

api_addr     = "http://0.0.0.0:8200"
cluster_addr = "http://0.0.0.0:8201"

# Логирование
log_level    = "info"
log_file     = "/vault/logs/vault.log"
