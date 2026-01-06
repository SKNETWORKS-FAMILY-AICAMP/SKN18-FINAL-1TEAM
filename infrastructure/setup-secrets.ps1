# Setup Secrets Manager with Database Credentials

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Secrets Manager Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Get RDS Endpoint
Write-Host "1. Retrieving RDS endpoint..." -ForegroundColor Yellow
$rdsInfo = (aws rds describe-db-instances --db-instance-identifier realestate-postgres --output json | ConvertFrom-Json)
$RDS_ENDPOINT = $rdsInfo.DBInstances[0].Endpoint.Address

Write-Host "  RDS Endpoint: $RDS_ENDPOINT" -ForegroundColor Green
Write-Host ""

# PostgreSQL Credentials
Write-Host "2. Creating PostgreSQL secret..." -ForegroundColor Yellow
$postgresSecret = @{
    username = "postgres"
    password = "RealEstate2024!Secure"
    host = $RDS_ENDPOINT
    port = "5432"
    database = "realestate"
} | ConvertTo-Json -Compress

try {
    aws secretsmanager create-secret `
      --name realestate/postgres `
      --description "PostgreSQL credentials for RDS" `
      --secret-string $postgresSecret 2>$null | Out-Null
    Write-Host "  ✅ PostgreSQL secret created" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Secret already exists, updating..." -ForegroundColor Yellow
    aws secretsmanager update-secret `
      --secret-id realestate/postgres `
      --secret-string $postgresSecret | Out-Null
    Write-Host "  ✅ PostgreSQL secret updated" -ForegroundColor Green
}

# Neo4j Credentials
Write-Host "3. Creating Neo4j secret..." -ForegroundColor Yellow
$neo4jSecret = @{
    username = "neo4j"
    password = "Neo4j2024!Secure"
    uri = "bolt://13.124.11.170:7687"
} | ConvertTo-Json -Compress

try {
    aws secretsmanager create-secret `
      --name realestate/neo4j `
      --description "Neo4j credentials" `
      --secret-string $neo4jSecret 2>$null | Out-Null
    Write-Host "  ✅ Neo4j secret created" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Secret already exists, updating..." -ForegroundColor Yellow
    aws secretsmanager update-secret `
      --secret-id realestate/neo4j `
      --secret-string $neo4jSecret | Out-Null
    Write-Host "  ✅ Neo4j secret updated" -ForegroundColor Green
}

# Elasticsearch Configuration
Write-Host "4. Creating Elasticsearch secret..." -ForegroundColor Yellow
$esSecret = @{
    host = "43.201.29.36"
    port = "9200"
} | ConvertTo-Json -Compress

try {
    aws secretsmanager create-secret `
      --name realestate/elasticsearch `
      --description "Elasticsearch configuration" `
      --secret-string $esSecret 2>$null | Out-Null
    Write-Host "  ✅ Elasticsearch secret created" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Secret already exists, updating..." -ForegroundColor Yellow
    aws secretsmanager update-secret `
      --secret-id realestate/elasticsearch `
      --secret-string $esSecret | Out-Null
    Write-Host "  ✅ Elasticsearch secret updated" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Secrets Manager Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Save connection info
$connectionInfo = @"
=== Database Connection Information ===

PostgreSQL (RDS):
  Host: $RDS_ENDPOINT
  Port: 5432
  Database: realestate
  Username: postgres
  Password: RealEstate2024!Secure

Neo4j (EC2):
  URI: bolt://13.124.11.170:7687
  Username: neo4j
  Password: Neo4j2024!Secure

Elasticsearch (EC2):
  URL: http://43.201.29.36:9200

Secrets Manager:
  - realestate/postgres
  - realestate/neo4j
  - realestate/elasticsearch
"@

$connectionInfo | Out-File -FilePath "database-connections.txt" -Encoding utf8

Write-Host "Connection info saved to: database-connections.txt" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Test database connections" -ForegroundColor White
Write-Host "2. Phase 3: Docker image preparation" -ForegroundColor White
