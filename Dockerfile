# Usar imagem oficial leve do Python
FROM python:3.9-slim

# Definir diretório de trabalho
WORKDIR /app

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ORAEX_SECRET_KEY=producao-super-secreta-alterar-isso

# Instalar dependências do sistema necessárias (opcional, mas comum)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Expor a porta 5000
EXPOSE 5000

# Comando para rodar a aplicação
# Usando gunicorn para produção seria melhor, mas para intranet python app.py com host 0.0.0.0 serve
CMD ["python", "app.py"]
