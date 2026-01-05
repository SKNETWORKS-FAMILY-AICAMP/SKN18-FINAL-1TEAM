# AWS Resources Verification Script
# Check all created resources

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AWS Resources Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
Write-Host "AWS Account ID: $AWS_ACCOUNT_ID" -ForegroundColor Green
Write-Host ""

# VPC
Write-Host "Checking VPC..." -ForegroundColor Yellow
$VPC_ID = (aws ec2 describe-vpcs --filters "Name=tag:Name,Values=realestate-vpc" --query "Vpcs[0].VpcId" --output text 2>$null)
if ($VPC_ID -and $VPC_ID -ne "None") {
    Write-Host "  VPC ID: $VPC_ID" -ForegroundColor Green
} else {
    Write-Host "  VPC not found!" -ForegroundColor Red
}

# Subnets
Write-Host "Checking Subnets..." -ForegroundColor Yellow
$SUBNETS = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].[SubnetId,Tags[?Key=='Name'].Value|[0],CidrBlock]" --output text 2>$null)
if ($SUBNETS) {
    $SUBNETS -split "`n" | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Green
    }
} else {
    Write-Host "  Subnets not found!" -ForegroundColor Red
}

# Security Group
Write-Host "Checking Security Group..." -ForegroundColor Yellow
$SG_ID = (aws ec2 describe-security-groups --filters "Name=group-name,Values=realestate-sg" --query "SecurityGroups[0].GroupId" --output text 2>$null)
if ($SG_ID -and $SG_ID -ne "None") {
    Write-Host "  Security Group ID: $SG_ID" -ForegroundColor Green
} else {
    Write-Host "  Security Group not found!" -ForegroundColor Red
}

# Internet Gateway
Write-Host "Checking Internet Gateway..." -ForegroundColor Yellow
$IGW_ID = (aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC_ID" --query "InternetGateways[0].InternetGatewayId" --output text 2>$null)
if ($IGW_ID -and $IGW_ID -ne "None") {
    Write-Host "  Internet Gateway ID: $IGW_ID" -ForegroundColor Green
} else {
    Write-Host "  Internet Gateway not found!" -ForegroundColor Red
}

# S3 Bucket
Write-Host "Checking S3 Bucket..." -ForegroundColor Yellow
$S3_CHECK = (aws s3 ls | Select-String "realestate-etl-data")
if ($S3_CHECK) {
    Write-Host "  S3 Bucket: realestate-etl-data" -ForegroundColor Green
} else {
    Write-Host "  S3 Bucket not found!" -ForegroundColor Red
}

# IAM Roles
Write-Host "Checking IAM Roles..." -ForegroundColor Yellow
$ECS_EXEC_ROLE = (aws iam get-role --role-name realestate-ecs-execution-role --query "Role.Arn" --output text 2>$null)
if ($ECS_EXEC_ROLE) {
    Write-Host "  ECS Execution Role: $ECS_EXEC_ROLE" -ForegroundColor Green
} else {
    Write-Host "  ECS Execution Role not found!" -ForegroundColor Red
}

$ECS_TASK_ROLE = (aws iam get-role --role-name realestate-ecs-task-role --query "Role.Arn" --output text 2>$null)
if ($ECS_TASK_ROLE) {
    Write-Host "  ECS Task Role: $ECS_TASK_ROLE" -ForegroundColor Green
} else {
    Write-Host "  ECS Task Role not found!" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Verification Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Save to file
$output = @"
# AWS Resources Created
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
VPC_ID=$VPC_ID
SG_ID=$SG_ID
IGW_ID=$IGW_ID
ECS_EXECUTION_ROLE_ARN=$ECS_EXEC_ROLE
ECS_TASK_ROLE_ARN=$ECS_TASK_ROLE
S3_BUCKET=realestate-etl-data
"@

$output | Out-File -FilePath "aws-resources-verified.txt" -Encoding utf8
Write-Host ""
Write-Host "Resource IDs saved to: aws-resources-verified.txt" -ForegroundColor Green
