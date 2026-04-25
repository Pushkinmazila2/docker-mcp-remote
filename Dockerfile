FROM python:3.12-alpine
WORKDIR /app
RUN apk add --no-cache gcc musl-dev linux-headers
RUN pip install --no-cache-dir mcp[cli] docker uvicorn
COPY server.py .
RUN apk del gcc musl-dev linux-headers
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
