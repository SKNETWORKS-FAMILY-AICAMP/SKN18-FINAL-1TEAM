# AWS ETL 파이프라인 자동 설정 스크립트 (PowerShell)
# 사용법: .\setup-aws.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AWS ETL 파이프라인 자동 설정 시작" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# AWS 계정 ID 가져오기
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$AWS_REGION = "ap-northeast-2"

Write-Host "AWS Account ID: $AWS_ACCOUNT_ID" -ForegroundColor Green
Write-Host "AWS Region: $AWS_REGION" -ForegroundColor Green
Write-Host ""

# 리소스 ID 저장 파일
$RESOURCE_FILE = "aws-resources.env"

# 함수: 리소스 ID 저장
function Save-Resource {
    param($key, $value)
    
    $content = Get-Content $RESOURCE_FILE -ErrorAction SilentlyContinue
    $pattern = "^export $key="
    
    if ($content -match $pattern) {
        $content = $content -replace $pattern + ".*", "export $key=`"$value`""
        $content | Set-Content $RESOURCE_FILE
    } else {
        Add-Content $RESOURCE_FILE "export $key=`"$value`""
    }
    
    Write-Host "✅ $key 저장: $value" -ForegroundColor Green
}

# Phase 1: VPC 및 네트워크 생성
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Phase 1: VPC 및 네트워크 생성" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# VPC 생성
Write-Host "VPC 생성 중..." -ForegroundColor Yellow
$VPC_ID = (aws ec2 create-vpc `
  --cidr-block 10.0.0.0/16 `
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=realestate-vpc}]' `
  --query 'Vpc.VpcId' `
  --output text)
Save-Resource "VPC_ID" $VPC_ID

# DNS 호스트 이름 활성화
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames | Out-Null
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support | Out-Null

# Public Subnet 생성
Write-Host "Public Subnet 생성 중..." -ForegroundColor Yellow
$PUBLIC_SUBNET_1 = (aws ec2 create-subnet `
  --vpc-id $VPC_ID `
  --cidr-block 10.0.1.0/24 `
  --availability-zone ap-northeast-2a `
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=realestate-public-1}]' `
  --query 'Subnet.SubnetId' `
  --output text)
Save-Resource "PUBLIC_SUBNET_1" $PUBLIC_SUBNET_1

$PUBLIC_SUBNET_2 = (aws ec2 create-subnet `
  --vpc-id $VPC_ID `
  --cidr-block 10.0.2.0/24 `
  --availability-zone ap-northeast-2c `
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=realestate-public-2}]' `
  --query 'Subnet.SubnetId' `
  --output text)
Save-Resource "PUBLIC_SUBNET_2" $PUBLIC_SUBNET_2

# Private Subnet 생성
Write-Host "Private Subnet 생성 중..." -ForegroundColor Yellow
$PRIVATE_SUBNET_1 = (aws ec2 create-subnet `
  --vpc-id $VPC_ID `
  --cidr-block 10.0.11.0/24 `
  --availability-zone ap-northeast-2a `
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=realestate-private-1}]' `
  --query 'Subnet.SubnetId' `
  --output text)
Save-Resource "PRIVATE_SUBNET_1" $PRIVATE_SUBNET_1

$PRIVATE_SUBNET_2 = (aws ec2 create-subnet `
  --vpc-id $VPC_ID `
  --cidr-block 10.0.12.0/24 `
  --availability-zone ap-northeast-2c `
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=realestate-private-2}]' `
  --query 'Subnet.SubnetId' `
  --output text)
Save-Resource "PRIVATE_SUBNET_2" $PRIVATE_SUBNET_2

# Internet Gateway 생성
Write-Host "Internet Gateway 생성 중..." -ForegroundColor Yellow
$IGW_ID = (aws ec2 create-internet-gateway `
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=realestate-igw}]' `
  --query 'InternetGateway.InternetGatewayId' `
  --output text)
Save-Resource "IGW_ID" $IGW_ID

aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID | Out-Null

# 라우팅 테이블 생성
Write-Host "라우팅 테이블 생성 중..." -ForegroundColor Yellow
$ROUTE_TABLE_ID = (aws ec2 create-route-table `
  --vpc-id $VPC_ID `
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=realestate-public-rt}]' `
  --query 'RouteTable.RouteTableId' `
  --output text)
Save-Resource "ROUTE_TABLE_ID" $ROUTE_TABLE_ID

aws ec2 create-route `
  --route-table-id $ROUTE_TABLE_ID `
  --destination-cidr-block 0.0.0.0/0 `
  --gateway-id $IGW_ID | Out-Null

aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_1 --route-table-id $ROUTE_TABLE_ID | Out-Null
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_2 --route-table-id $ROUTE_TABLE_ID | Out-Null

# 보안 그룹 생성
Write-Host "보안 그룹 생성 중..." -ForegroundColor Yellow
$SG_ID = (aws ec2 create-security-group `
  --group-name realestate-sg `
  --description "Security group for realestate ETL pipeline" `
  --vpc-id $VPC_ID `
  --query 'GroupId' `
  --output text)
Save-Resource "SG_ID" $SG_ID

# 보안 그룹 규칙 추가
Write-Host "보안 그룹 규칙 추가 중..." -ForegroundColor Yellow
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol all --source-group $SG_ID | Out-Null
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr 10.0.0.0/16 | Out-Null
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 7687 --cidr 10.0.0.0/16 | Out-Null
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 9200 --cidr 10.0.0.0/16 | Out-Null
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 | Out-Null

Write-Host "✅ Phase 1 완료: VPC 및 네트워크 생성 완료" -ForegroundColor Green

# Phase 2: IAM 역할 생성
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Phase 2: IAM 역할 생성" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Trust Policy 파일 생성
$ecsTrustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@
$ecsTrustPolicy | Out-File -FilePath "ecs-trust-policy.json" -Encoding utf8

# ECS Execution Role 생성
Write-Host "ECS Execution Role 생성 중..." -ForegroundColor Yellow
try {
    aws iam create-role `
      --role-name realestate-ecs-execution-role `
      --assume-role-policy-document file://ecs-trust-policy.json | Out-Null
} catch {
    Write-Host "⚠️  Role이 이미 존재합니다. 계속 진행..." -ForegroundColor Yellow
}

aws iam attach-role-policy `
  --role-name realestate-ecs-execution-role `
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy | Out-Null

# Secrets Manager 접근 정책
$secretsPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "kms:Decrypt"
      ],
      "Resource": "*"
    }
  ]
}
"@
$secretsPolicy | Out-File -FilePath "ecs-secrets-policy.json" -Encoding utf8

aws iam put-role-policy `
  --role-name realestate-ecs-execution-role `
  --policy-name SecretsManagerAccess `
  --policy-document file://ecs-secrets-policy.json | Out-Null

$ECS_EXECUTION_ROLE_ARN = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-execution-role"
Save-Resource "ECS_EXECUTION_ROLE_ARN" $ECS_EXECUTION_ROLE_ARN

# ECS Task Role 생성
Write-Host "ECS Task Role 생성 중..." -ForegroundColor Yellow
try {
    aws iam create-role `
      --role-name realestate-ecs-task-role `
      --assume-role-policy-document file://ecs-trust-policy.json | Out-Null
} catch {
    Write-Host "⚠️  Role이 이미 존재합니다. 계속 진행..." -ForegroundColor Yellow
}

$s3Policy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::realestate-etl-data/*",
        "arn:aws:s3:::realestate-etl-data"
      ]
    }
  ]
}
"@
$s3Policy | Out-File -FilePath "ecs-s3-policy.json" -Encoding utf8

aws iam put-role-policy `
  --role-name realestate-ecs-task-role `
  --policy-name S3Access `
  --policy-document file://ecs-s3-policy.json | Out-Null

$ECS_TASK_ROLE_ARN = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-task-role"
Save-Resource "ECS_TASK_ROLE_ARN" $ECS_TASK_ROLE_ARN

Write-Host "✅ Phase 2 완료: IAM 역할 생성 완료" -ForegroundColor Green

# Phase 3: S3 버킷 생성
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Phase 3: S3 버킷 생성" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "S3 버킷 생성 중..." -ForegroundColor Yellow
try {
    aws s3 mb s3://realestate-etl-data --region ap-northeast-2 | Out-Null
    Write-Host "✅ S3 버킷 생성 완료" -ForegroundColor Green
} catch {
    Write-Host "⚠️  S3 버킷이 이미 존재합니다." -ForegroundColor Yellow
}

Save-Resource "S3_BUCKET" "realestate-etl-data"

# 정리
Remove-Item ecs-trust-policy.json -ErrorAction SilentlyContinue
Remove-Item ecs-secrets-policy.json -ErrorAction SilentlyContinue
Remove-Item ecs-s3-policy.json -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Created Resources:" -ForegroundColor Cyan
Write-Host "  - VPC: $VPC_ID" -ForegroundColor White
Write-Host "  - Public Subnets: $PUBLIC_SUBNET_1, $PUBLIC_SUBNET_2" -ForegroundColor White
Write-Host "  - Private Subnets: $PRIVATE_SUBNET_1, $PRIVATE_SUBNET_2" -ForegroundColor White
Write-Host "  - Security Group: $SG_ID" -ForegroundColor White
Write-Host "  - S3 Bucket: realestate-etl-data" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Check aws-resources.env file" -ForegroundColor White
Write-Host "2. Create RDS PostgreSQL" -ForegroundColor White
Write-Host "3. Setup EC2 Neo4j server" -ForegroundColor White
Write-Host "4. Setup EC2 Elasticsearch server" -ForegroundColor White
Write-Host "5. Build and push Docker image to ECR" -ForegroundColor White
Write-Host ""
Write-Host "For detailed guide, see: implementation_plan.md" -ForegroundColor Cyan
