# Fix Secrets Manager - Recreate with proper JSON format

Write-Host "Fixing Secrets Manager..." -ForegroundColor Cyan
Write-Host ""

# Get RDS endpoint
$RDS_ENDPOINT = "realestate-postgres.cx0uwsiue937.ap-northeast-2.rds.amazonaws.com"

# Delete and recreate PostgreSQL secret
Write-Host "1. Recreating PostgreSQL secret..." -ForegroundColor Yellow
aws secretsmanager delete-secret --secret-id realestate/postgres --force-delete-without-recovery --region ap-northeast-2 2>$null | Out-Null

$postgresSecret = '{"username":"postgres","password":"RealEstate2024!Secure","host":"' + $RDS_ENDPOINT + '","port":"5432","database":"realestate"}'

aws secretsmanager create-secret `
  --name realestate/postgres `
  --description "PostgreSQL credentials" `
  --secret-string $postgresSecret `
  --region ap-northeast-2 | Out-Null

Write-Host "  ✅ PostgreSQL secret recreated" -ForegroundColor Green

# Delete and recreate Neo4j secret
Write-Host "2. Recreating Neo4j secret..." -ForegroundColor Yellow
aws secretsmanager delete-secret --secret-id realestate/neo4j --force-delete-without-recovery --region ap-northeast-2 2>$null | Out-Null

$neo4jSecret = '{"username":"neo4j","password":"Neo4j2024!Secure","uri":"bolt://13.124.11.170:7687"}'

aws secretsmanager create-secret `
  --name realestate/neo4j `
  --description "Neo4j credentials" `
  --secret-string $neo4jSecret `
  --region ap-northeast-2 | Out-Null

Write-Host "  ✅ Neo4j secret recreated" -ForegroundColor Green

# Delete and recreate Elasticsearch secret
Write-Host "3. Recreating Elasticsearch secret..." -ForegroundColor Yellow
aws secretsmanager delete-secret --secret-id realestate/elasticsearch --force-delete-without-recovery --region ap-northeast-2 2>$null | Out-Null

$esSecret = '{"host":"43.201.29.36","port":"9200"}'

aws secretsmanager create-secret `
  --name realestate/elasticsearch `
  --description "Elasticsearch configuration" `
  --secret-string $esSecret `
  --region ap-northeast-2 | Out-Null

Write-Host "  ✅ Elasticsearch secret recreated" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Secrets Manager Fixed!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Verify secrets:" -ForegroundColor Cyan
Write-Host "  aws secretsmanager get-secret-value --secret-id realestate/postgres --query SecretString --output text" -ForegroundColor Gray
Write-Host ""
Write-Host "Now retry the ECS task!" -ForegroundColor Green
