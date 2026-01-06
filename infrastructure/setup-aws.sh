#!/bin/bash
# AWS ETL 파이프라인 자동 설정 스크립트
# 사용법: ./setup-aws.sh

set -e

echo "=========================================="
echo "AWS ETL 파이프라인 자동 설정 시작"
echo "=========================================="

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# AWS 계정 ID 가져오기
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION="ap-northeast-2"

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"

# 리소스 ID 저장 파일
RESOURCE_FILE="aws-resources.env"

# 함수: 리소스 ID 저장
save_resource() {
    local key=$1
    local value=$2
    if grep -q "^export $key=" "$RESOURCE_FILE"; then
        sed -i "s|^export $key=.*|export $key=\"$value\"|" "$RESOURCE_FILE"
    else
        echo "export $key=\"$value\"" >> "$RESOURCE_FILE"
    fi
    echo "✅ $key 저장: $value"
}

# Phase 1: VPC 및 네트워크 생성
echo ""
echo "=========================================="
echo "Phase 1: VPC 및 네트워크 생성"
echo "=========================================="

# VPC 생성
echo "VPC 생성 중..."
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=realestate-vpc}]' \
  --query 'Vpc.VpcId' \
  --output text)
save_resource "VPC_ID" "$VPC_ID"

# DNS 호스트 이름 활성화
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support

# Public Subnet 생성
echo "Public Subnet 생성 중..."
PUBLIC_SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone ap-northeast-2a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=realestate-public-1}]' \
  --query 'Subnet.SubnetId' \
  --output text)
save_resource "PUBLIC_SUBNET_1" "$PUBLIC_SUBNET_1"

PUBLIC_SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone ap-northeast-2c \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=realestate-public-2}]' \
  --query 'Subnet.SubnetId' \
  --output text)
save_resource "PUBLIC_SUBNET_2" "$PUBLIC_SUBNET_2"

# Private Subnet 생성
echo "Private Subnet 생성 중..."
PRIVATE_SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.11.0/24 \
  --availability-zone ap-northeast-2a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=realestate-private-1}]' \
  --query 'Subnet.SubnetId' \
  --output text)
save_resource "PRIVATE_SUBNET_1" "$PRIVATE_SUBNET_1"

PRIVATE_SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.12.0/24 \
  --availability-zone ap-northeast-2c \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=realestate-private-2}]' \
  --query 'Subnet.SubnetId' \
  --output text)
save_resource "PRIVATE_SUBNET_2" "$PRIVATE_SUBNET_2"

# Internet Gateway 생성
echo "Internet Gateway 생성 중..."
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=realestate-igw}]' \
  --query 'InternetGateway.InternetGatewayId' \
  --output text)
save_resource "IGW_ID" "$IGW_ID"

aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

# 라우팅 테이블 생성
echo "라우팅 테이블 생성 중..."
ROUTE_TABLE_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=realestate-public-rt}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)
save_resource "ROUTE_TABLE_ID" "$ROUTE_TABLE_ID"

aws ec2 create-route \
  --route-table-id $ROUTE_TABLE_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_1 --route-table-id $ROUTE_TABLE_ID
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_2 --route-table-id $ROUTE_TABLE_ID

# 보안 그룹 생성
echo "보안 그룹 생성 중..."
SG_ID=$(aws ec2 create-security-group \
  --group-name realestate-sg \
  --description "Security group for realestate ETL pipeline" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)
save_resource "SG_ID" "$SG_ID"

# 보안 그룹 규칙 추가
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol all --source-group $SG_ID
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr 10.0.0.0/16
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 7687 --cidr 10.0.0.0/16
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 9200 --cidr 10.0.0.0/16
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0

echo "✅ Phase 1 완료: VPC 및 네트워크 생성 완료"

# Phase 2: IAM 역할 생성
echo ""
echo "=========================================="
echo "Phase 2: IAM 역할 생성"
echo "=========================================="

# Trust Policy 파일 생성
cat > /tmp/ecs-trust-policy.json << 'EOF'
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
EOF

# ECS Execution Role 생성
echo "ECS Execution Role 생성 중..."
aws iam create-role \
  --role-name realestate-ecs-execution-role \
  --assume-role-policy-document file:///tmp/ecs-trust-policy.json || true

aws iam attach-role-policy \
  --role-name realestate-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Secrets Manager 접근 정책
cat > /tmp/ecs-secrets-policy.json << 'EOF'
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
EOF

aws iam put-role-policy \
  --role-name realestate-ecs-execution-role \
  --policy-name SecretsManagerAccess \
  --policy-document file:///tmp/ecs-secrets-policy.json

ECS_EXECUTION_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-execution-role"
save_resource "ECS_EXECUTION_ROLE_ARN" "$ECS_EXECUTION_ROLE_ARN"

# ECS Task Role 생성
echo "ECS Task Role 생성 중..."
aws iam create-role \
  --role-name realestate-ecs-task-role \
  --assume-role-policy-document file:///tmp/ecs-trust-policy.json || true

cat > /tmp/ecs-s3-policy.json << 'EOF'
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
EOF

aws iam put-role-policy \
  --role-name realestate-ecs-task-role \
  --policy-name S3Access \
  --policy-document file:///tmp/ecs-s3-policy.json

ECS_TASK_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-task-role"
save_resource "ECS_TASK_ROLE_ARN" "$ECS_TASK_ROLE_ARN"

echo "✅ Phase 2 완료: IAM 역할 생성 완료"

echo ""
echo "=========================================="
echo "✅ 자동 설정 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "1. aws-resources.env 파일 확인"
echo "2. RDS, Neo4j, Elasticsearch 수동 설정"
echo "3. Docker 이미지 빌드 및 ECR 푸시"
echo "4. ECS 태스크 정의 등록"
echo "5. EventBridge 스케줄 설정"
echo ""
echo "상세 가이드: implementation_plan.md 참조"
