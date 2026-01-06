# Create DB Subnet Group for RDS
# Run this before creating RDS instance

Write-Host "Creating DB Subnet Group..." -ForegroundColor Cyan

$VPC_ID = "vpc-0edc6bd52bea8f771"

# Get Private Subnets
$SUBNETS = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].[SubnetId,Tags[?Key=='Name'].Value|[0]]" --output json | ConvertFrom-Json)
$PRIVATE_SUBNET_1 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-private-1" })[0]
$PRIVATE_SUBNET_2 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-private-2" })[0]

Write-Host "Private Subnet 1: $PRIVATE_SUBNET_1" -ForegroundColor Green
Write-Host "Private Subnet 2: $PRIVATE_SUBNET_2" -ForegroundColor Green
Write-Host ""

# Create DB Subnet Group
Write-Host "Creating DB Subnet Group 'realestate-db-subnet-group'..." -ForegroundColor Yellow

aws rds create-db-subnet-group `
  --db-subnet-group-name realestate-db-subnet-group `
  --db-subnet-group-description "Subnet group for RDS PostgreSQL" `
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 `
  --tags Key=Name,Value=realestate-db-subnet-group

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ DB Subnet Group created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Now you can create RDS in AWS Console:" -ForegroundColor Cyan
    Write-Host "1. Refresh the RDS creation page" -ForegroundColor White
    Write-Host "2. In 'DB subnet group' dropdown, select: realestate-db-subnet-group" -ForegroundColor White
    Write-Host "3. Continue with RDS creation" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "⚠️  Error creating DB Subnet Group" -ForegroundColor Red
    Write-Host "It may already exist. Check in AWS Console:" -ForegroundColor Yellow
    Write-Host "  RDS → Subnet groups" -ForegroundColor White
}
