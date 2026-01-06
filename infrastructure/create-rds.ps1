# Manual RDS Creation Script
# Creates RDS PostgreSQL with proper error handling

Write-Host "Creating RDS PostgreSQL..." -ForegroundColor Cyan

$VPC_ID = "vpc-0edc6bd52bea8f771"
$SG_ID = "sg-0b2bdef4bce788976"
$DB_PASSWORD = "RealEstate2024!Secure"

# Get Private Subnets
$SUBNETS = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].[SubnetId,Tags[?Key=='Name'].Value|[0]]" --output json | ConvertFrom-Json)
$PRIVATE_SUBNET_1 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-private-1" })[0]
$PRIVATE_SUBNET_2 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-private-2" })[0]

Write-Host "Private Subnets: $PRIVATE_SUBNET_1, $PRIVATE_SUBNET_2" -ForegroundColor Green

# Create DB Subnet Group
Write-Host "Creating DB Subnet Group..." -ForegroundColor Yellow
$subnetGroupResult = aws rds create-db-subnet-group `
  --db-subnet-group-name realestate-db-subnet-group `
  --db-subnet-group-description "Subnet group for RDS" `
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 2>&1

if ($LASTEXITCODE -ne 0) {
    if ($subnetGroupResult -like "*DBSubnetGroupAlreadyExists*") {
        Write-Host "  DB Subnet Group already exists" -ForegroundColor Yellow
    } else {
        Write-Host "  Error: $subnetGroupResult" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  DB Subnet Group created successfully" -ForegroundColor Green
}

# Create RDS Instance
Write-Host "Creating RDS PostgreSQL instance..." -ForegroundColor Yellow
Write-Host "  This will take 5-10 minutes..." -ForegroundColor Yellow

$rdsResult = aws rds create-db-instance `
  --db-instance-identifier realestate-postgres `
  --db-instance-class db.t3.micro `
  --engine postgres `
  --engine-version 15.4 `
  --master-username postgres `
  --master-user-password $DB_PASSWORD `
  --allocated-storage 20 `
  --storage-type gp3 `
  --db-name realestate `
  --vpc-security-group-ids $SG_ID `
  --db-subnet-group-name realestate-db-subnet-group `
  --publicly-accessible `
  --backup-retention-period 7 `
  --preferred-backup-window "03:00-04:00" `
  --preferred-maintenance-window "mon:04:00-mon:05:00" `
  --no-multi-az `
  --tags Key=Name,Value=realestate-postgres 2>&1

if ($LASTEXITCODE -ne 0) {
    if ($rdsResult -like "*DBInstanceAlreadyExists*") {
        Write-Host "  RDS instance already exists" -ForegroundColor Yellow
    } else {
        Write-Host "  Error: $rdsResult" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  RDS instance creation started!" -ForegroundColor Green
    Write-Host "  Instance ID: realestate-postgres" -ForegroundColor Green
    Write-Host "  Master Username: postgres" -ForegroundColor Green
    Write-Host "  Master Password: $DB_PASSWORD" -ForegroundColor Yellow
    Write-Host "  Database Name: realestate" -ForegroundColor Green
}

Write-Host ""
Write-Host "RDS creation initiated. Check status with:" -ForegroundColor Cyan
Write-Host "  aws rds describe-db-instances --db-instance-identifier realestate-postgres" -ForegroundColor White
