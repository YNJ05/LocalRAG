FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PDF_SERVICE_URL=http://pdf-microservice:8001 \
    RAG_SERVICE_URL=http://rag-microservice:8002 \
    CHAT_SERVICE_URL=http://chat-microservice:8003

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_ui.py .

EXPOSE 8501

CMD ["streamlit", "run", "app_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
