# Phase 2: Database Setup Script (Fixed)
# Creates RDS PostgreSQL, EC2 Neo4j, and EC2 Elasticsearch

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Phase 2: Database Infrastructure Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Load VPC and Security Group IDs
$VPC_ID = "vpc-0edc6bd52bea8f771"
$SG_ID = "sg-0b2bdef4bce788976"
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)

Write-Host "VPC ID: $VPC_ID" -ForegroundColor Green
Write-Host "Security Group ID: $SG_ID" -ForegroundColor Green
Write-Host ""

# Get Subnet IDs
Write-Host "Fetching subnet information..." -ForegroundColor Yellow
$SUBNETS = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].[SubnetId,Tags[?Key=='Name'].Value|[0]]" --output json | ConvertFrom-Json)

$PUBLIC_SUBNET_1 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-public-1" })[0]
$PUBLIC_SUBNET_2 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-public-2" })[0]
$PRIVATE_SUBNET_1 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-private-1" })[0]
$PRIVATE_SUBNET_2 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-private-2" })[0]

Write-Host "  Public Subnet 1: $PUBLIC_SUBNET_1" -ForegroundColor Green
Write-Host "  Public Subnet 2: $PUBLIC_SUBNET_2" -ForegroundColor Green
Write-Host "  Private Subnet 1: $PRIVATE_SUBNET_1" -ForegroundColor Green
Write-Host "  Private Subnet 2: $PRIVATE_SUBNET_2" -ForegroundColor Green
Write-Host ""

# ============================================
# 1. RDS PostgreSQL Setup
# ============================================
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "1. Creating RDS PostgreSQL" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# DB Subnet Group
Write-Host "Creating DB Subnet Group..." -ForegroundColor Yellow
try {
    aws rds create-db-subnet-group `
      --db-subnet-group-name realestate-db-subnet-group `
      --db-subnet-group-description "Subnet group for RDS" `
      --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 2>$null | Out-Null
    Write-Host "  DB Subnet Group created" -ForegroundColor Green
} catch {
    Write-Host "  DB Subnet Group already exists" -ForegroundColor Yellow
}

# RDS Instance
Write-Host "Creating RDS PostgreSQL instance..." -ForegroundColor Yellow
Write-Host "  This will take 5-10 minutes..." -ForegroundColor Yellow

$DB_PASSWORD = "RealEstate2024!Secure"

try {
    aws rds create-db-instance `
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
      --tags Key=Name,Value=realestate-postgres 2>$null | Out-Null
    
    Write-Host "  RDS instance creation started!" -ForegroundColor Green
    Write-Host "  Instance ID: realestate-postgres" -ForegroundColor Green
    Write-Host "  Master Username: postgres" -ForegroundColor Green
    Write-Host "  Master Password: $DB_PASSWORD" -ForegroundColor Yellow
    Write-Host "  Database Name: realestate" -ForegroundColor Green
    
    # Save credentials
    "=== RDS PostgreSQL ===" | Out-File -FilePath "db-credentials.txt" -Encoding utf8
    "Master Username: postgres" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "Master Password: $DB_PASSWORD" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "Database Name: realestate" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    
} catch {
    Write-Host "  RDS instance already exists or error occurred" -ForegroundColor Yellow
}

Write-Host ""

# ============================================
# 2. EC2 Neo4j Server Setup
# ============================================
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "2. Creating EC2 Neo4j Server" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Create Key Pair if not exists
Write-Host "Checking SSH key pair..." -ForegroundColor Yellow
$KEY_EXISTS = (aws ec2 describe-key-pairs --key-names realestate-key 2>$null)
if (-not $KEY_EXISTS) {
    Write-Host "Creating new key pair..." -ForegroundColor Yellow
    aws ec2 create-key-pair --key-name realestate-key --query 'KeyMaterial' --output text | Out-File -FilePath "realestate-key.pem" -Encoding ascii
    Write-Host "  Key saved to: realestate-key.pem" -ForegroundColor Green
} else {
    Write-Host "  Key pair already exists" -ForegroundColor Green
}

# Get latest Ubuntu AMI
Write-Host "Finding latest Ubuntu AMI..." -ForegroundColor Yellow
$AMI_ID = (aws ec2 describe-images `
  --owners 099720109477 `
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" `
  --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' `
  --output text)
Write-Host "  AMI ID: $AMI_ID" -ForegroundColor Green

# Neo4j User Data (base64 encoded)
$NEO4J_PASSWORD = "Neo4j2024!Secure"
$neo4jScript = @"
#!/bin/bash
apt-get update && apt-get install -y openjdk-17-jdk wget
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | apt-key add -
echo 'deb https://debian.neo4j.com stable latest' > /etc/apt/sources.list.d/neo4j.list
apt-get update && apt-get install -y neo4j=1:5.15.0
wget https://github.com/neo4j/apoc/releases/download/5.15.0/apoc-5.15.0-core.jar -O /var/lib/neo4j/plugins/apoc-5.15.0-core.jar
echo 'server.default_listen_address=0.0.0.0' >> /etc/neo4j/neo4j.conf
echo 'dbms.security.procedures.unrestricted=apoc.*' >> /etc/neo4j/neo4j.conf
neo4j-admin dbms set-initial-password '$NEO4J_PASSWORD'
systemctl enable neo4j && systemctl start neo4j
"@

# Launch Neo4j EC2 instance
Write-Host "Launching Neo4j EC2 instance..." -ForegroundColor Yellow
try {
    $NEO4J_INSTANCE = (aws ec2 run-instances `
      --image-id $AMI_ID `
      --instance-type t3.micro `
      --key-name realestate-key `
      --security-group-ids $SG_ID `
      --subnet-id $PUBLIC_SUBNET_1 `
      --associate-public-ip-address `
      --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=realestate-neo4j}]' `
      --user-data $neo4jScript `
      --query 'Instances[0].InstanceId' `
      --output text)
    
    Write-Host "  Neo4j instance created: $NEO4J_INSTANCE" -ForegroundColor Green
    Write-Host "  Password: $NEO4J_PASSWORD" -ForegroundColor Yellow
    
    # Save credentials
    "=== Neo4j ===" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "Username: neo4j" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "Password: $NEO4J_PASSWORD" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "Instance ID: $NEO4J_INSTANCE" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    
    # Wait for public IP
    Start-Sleep -Seconds 15
    $NEO4J_IP = (aws ec2 describe-instances --instance-ids $NEO4J_INSTANCE --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
    
    Write-Host "  Public IP: $NEO4J_IP" -ForegroundColor Green
    Write-Host "  Connection URI: bolt://$NEO4J_IP:7687" -ForegroundColor Cyan
    
    "Public IP: $NEO4J_IP" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "URI: bolt://$NEO4J_IP:7687" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    
} catch {
    Write-Host "  Error: $_" -ForegroundColor Red
}

Write-Host ""

# ============================================
# 3. EC2 Elasticsearch Server Setup
# ============================================
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "3. Creating EC2 Elasticsearch Server" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Elasticsearch User Data
$esScript = @"
#!/bin/bash
apt-get update && apt-get install -y openjdk-17-jdk wget
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
echo 'deb https://artifacts.elastic.co/packages/8.x/apt stable main' > /etc/apt/sources.list.d/elastic-8.x.list
apt-get update && apt-get install -y elasticsearch=8.11.0
echo 'network.host: 0.0.0.0' >> /etc/elasticsearch/elasticsearch.yml
echo 'xpack.security.enabled: false' >> /etc/elasticsearch/elasticsearch.yml
systemctl enable elasticsearch && systemctl start elasticsearch
"@

# Launch Elasticsearch EC2 instance
Write-Host "Launching Elasticsearch EC2 instance..." -ForegroundColor Yellow
try {
    $ES_INSTANCE = (aws ec2 run-instances `
      --image-id $AMI_ID `
      --instance-type t3.small `
      --key-name realestate-key `
      --security-group-ids $SG_ID `
      --subnet-id $PUBLIC_SUBNET_1 `
      --associate-public-ip-address `
      --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=realestate-elasticsearch}]' `
      --user-data $esScript `
      --query 'Instances[0].InstanceId' `
      --output text)
    
    Write-Host "  Elasticsearch instance created: $ES_INSTANCE" -ForegroundColor Green
    
    "=== Elasticsearch ===" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "Instance ID: $ES_INSTANCE" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    
    # Wait for public IP
    Start-Sleep -Seconds 15
    $ES_IP = (aws ec2 describe-instances --instance-ids $ES_INSTANCE --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
    
    Write-Host "  Public IP: $ES_IP" -ForegroundColor Green
    Write-Host "  Connection URL: http://$ES_IP:9200" -ForegroundColor Cyan
    
    "Public IP: $ES_IP" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    "URL: http://$ES_IP:9200" | Out-File -FilePath "db-credentials.txt" -Append -Encoding utf8
    
} catch {
    Write-Host "  Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Phase 2 Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Credentials saved to: db-credentials.txt" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: Wait 5-10 minutes for all services to initialize" -ForegroundColor Yellow
