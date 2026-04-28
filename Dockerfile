FROM python:3.12-slim

# openssh-client нужен для ssh-keygen, curl для проверки Vault
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Дефолтные volume-точки
VOLUME ["/data", "/keys"]

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]