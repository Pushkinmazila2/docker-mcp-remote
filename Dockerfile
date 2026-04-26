FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache curl libstdc++ \
    && apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers \
    && pip install --no-cache-dir mcp[cli] docker uvicorn starlette psutil \
    && apk del .build-deps \
    && rm -rf /root/.cache

COPY server.py .
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
