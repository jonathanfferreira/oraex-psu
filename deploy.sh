#!/bin/bash
# ══════════════════════════════════════════════════════════
# ORAEX PSU Manager — Deploy to Google Cloud Run
# ══════════════════════════════════════════════════════════
#
# Pré-requisitos:
#   1. gcloud CLI instalado: https://cloud.google.com/sdk/docs/install
#   2. Projeto GCP criado e billing habilitado
#   3. Docker instalado (apenas para teste local)
#
# Uso:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# ──────────────────────────────────────────────────────────

set -e

# ── CONFIGURAÇÃO (altere conforme necessário) ──
PROJECT_ID="oraex-cloud-consulting"  # ID do projeto Google Cloud
REGION="southamerica-east1"         # São Paulo
SERVICE_NAME="oraex-psu"            # Nome do serviço Cloud Run
BUCKET_NAME="${PROJECT_ID}-data"    # Bucket para persistência do SQLite
IMAGE_NAME="oraex-psu"

echo "════════════════════════════════════════"
echo "  ORAEX PSU Manager — Cloud Run Deploy"
echo "════════════════════════════════════════"

# ── 1. Login e configuração do projeto ──
echo ""
echo "🔐 Passo 1: Autenticação..."
gcloud auth login
gcloud config set project $PROJECT_ID

# ── 2. Habilitar APIs necessárias ──
echo ""
echo "🔧 Passo 2: Habilitando APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    storage.googleapis.com

# ── 3. Criar repositório no Artifact Registry ──
echo ""
echo "📦 Passo 3: Criando repositório de imagens..."
gcloud artifacts repositories create docker-repo \
    --repository-format=docker \
    --location=$REGION \
    --description="ORAEX Docker images" \
    2>/dev/null || echo "  (repositório já existe)"

# ── 4. Criar bucket GCS para persistência ──
echo ""
echo "🪣 Passo 4: Criando bucket para dados..."
gcloud storage buckets create gs://$BUCKET_NAME \
    --location=$REGION \
    --uniform-bucket-level-access \
    2>/dev/null || echo "  (bucket já existe)"

# ── 5. Build e push da imagem ──
echo ""
echo "🐳 Passo 5: Construindo e enviando imagem..."
IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/docker-repo/$IMAGE_NAME:latest"

gcloud builds submit --tag $IMAGE_URI .

# ── 6. Deploy no Cloud Run ──
echo ""
echo "🚀 Passo 6: Deploying no Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_URI \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 2 \
    --timeout 120 \
    --set-env-vars "DATABASE_PATH=/data/oraex.db,ORAEX_SECRET_KEY=$(openssl rand -hex 24),FLASK_DEBUG=false" \
    --execution-environment gen2 \
    --add-volume name=data-vol,type=cloud-storage,bucket=$BUCKET_NAME \
    --add-volume-mount volume=data-vol,mount-path=/data

echo ""
echo "════════════════════════════════════════"
echo "  ✅ Deploy concluído!"
echo ""
echo "  URL: $(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')"
echo ""
echo "  Login: admin / oraex2025"
echo "  (troque a senha após o primeiro acesso)"
echo "════════════════════════════════════════"
