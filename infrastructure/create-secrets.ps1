# Create Secrets Manager entries (clean approach)

Write-Host "Creating Secrets Manager entries..." -ForegroundColor Cyan
Write-Host ""

$RDS_ENDPOINT = "realestate-postgres.cx0uwsiue937.ap-northeast-2.rds.amazonaws.com"

# PostgreSQL
Write-Host "1. Creating PostgreSQL secret..." -ForegroundColor Yellow
$postgresJson = @{
    username = "postgres"
    password = "RealEstate2024!Secure"
    host = $RDS_ENDPOINT
    port = "5432"
    database = "realestate"
} | ConvertTo-Json -Compress

aws secretsmanager create-secret `
  --name "realestate/postgres" `
  --description "PostgreSQL credentials" `
  --secret-string $postgresJson `
  --region ap-northeast-2

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ PostgreSQL secret created" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  May already exist or error occurred" -ForegroundColor Yellow
}

Write-Host ""

# Neo4j
Write-Host "2. Creating Neo4j secret..." -ForegroundColor Yellow
$neo4jJson = @{
    username = "neo4j"
    password = "Neo4j2024!Secure"
    uri = "bolt://13.124.11.170:7687"
} | ConvertTo-Json -Compress

aws secretsmanager create-secret `
  --name "realestate/neo4j" `
  --description "Neo4j credentials" `
  --secret-string $neo4jJson `
  --region ap-northeast-2

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Neo4j secret created" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  May already exist or error occurred" -ForegroundColor Yellow
}

Write-Host ""

# Elasticsearch
Write-Host "3. Creating Elasticsearch secret..." -ForegroundColor Yellow
$esJson = @{
    host = "43.201.29.36"
    port = "9200"
} | ConvertTo-Json -Compress

aws secretsmanager create-secret `
  --name "realestate/elasticsearch" `
  --description "Elasticsearch configuration" `
  --secret-string $esJson `
  --region ap-northeast-2

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Elasticsearch secret created" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  May already exist or error occurred" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Secrets Created!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Verify:" -ForegroundColor Cyan
Write-Host "  aws secretsmanager list-secrets --query 'SecretList[?contains(Name, \`"realestate\`")].Name' --region ap-northeast-2" -ForegroundColor Gray
