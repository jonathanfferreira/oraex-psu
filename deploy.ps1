$ErrorActionPreference = "Stop"

$PROJECT_ID = "oraex-cloud-consulting"
$REGION = "southamerica-east1"
$SERVICE_NAME = "oraex-psu"
$BUCKET_NAME = "$PROJECT_ID-data"
$IMAGE_NAME = "oraex-psu"
$gcloud = "C:\Users\fferr\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "════════════════════════════════════════"
Write-Host "  ORAEX PSU Manager — Cloud Run Deploy (PS)"
Write-Host "════════════════════════════════════════"

Write-Host "`n🔐 Passo 1: Configuração..."
& $gcloud config set project $PROJECT_ID

Write-Host "`n🐳 Passo 5: Construindo e enviando imagem (Cloud Build)..."
$IMAGE_URI = "$REGION-docker.pkg.dev/$PROJECT_ID/docker-repo/${IMAGE_NAME}:latest"
& $gcloud builds submit --tag $IMAGE_URI .

Write-Host "`n🚀 Passo 6: Deploying no Cloud Run..."
$randomHex = -join ((48..57) + (97..102) | Get-Random -Count 48 | % {[char]$_})
$envVars = "DATABASE_PATH=/data/oraex.db,ORAEX_SECRET_KEY=$randomHex,FLASK_DEBUG=false"

& $gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_URI `
    --region $REGION `
    --platform managed `
    --allow-unauthenticated `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 2 `
    --timeout 120 `
    --set-env-vars $envVars `
    --execution-environment gen2 `
    --add-volume name=data-vol,type=cloud-storage,bucket=$BUCKET_NAME `
    --add-volume-mount volume=data-vol,mount-path=/data

Write-Host "`n✅ Deploy concluído!"
$url = & $gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)"
Write-Host "URL: $url"
