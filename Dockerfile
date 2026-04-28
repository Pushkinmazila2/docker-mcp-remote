FROM python:3.13-slim

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    openssh-client \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


COPY app/ ./app/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Дефолтные volume-точки
VOLUME ["/data", "/keys"]

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]