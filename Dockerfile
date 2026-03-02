# Imagem base leve do Python
FROM python:3.11-slim

WORKDIR /app

# Variáveis de ambiente para produção
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_DEBUG=false

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Cloud Run injeta a variável PORT automaticamente (default: 8080)
ENV PORT=8080
EXPOSE 8080

# Produção: gunicorn com timeout alto para uploads de planilhas grandes
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 120 app:app
