# Create Missing IAM Roles for ECS

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Creating IAM Roles for ECS" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$AWS_ACCOUNT_ID = "940075378738"

# ECS Trust Policy
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

# Step 1: Create ECS Execution Role
Write-Host "Step 1: Creating ECS Execution Role..." -ForegroundColor Yellow

try {
    aws iam create-role `
      --role-name realestate-ecs-execution-role `
      --assume-role-policy-document file://ecs-trust-policy.json `
      --description "ECS task execution role for realestate ETL" 2>$null | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Execution role created" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Role may already exist" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Role may already exist" -ForegroundColor Yellow
}

# Attach AWS managed policy
aws iam attach-role-policy `
  --role-name realestate-ecs-execution-role `
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy | Out-Null

Write-Host "  ✅ Attached AmazonECSTaskExecutionRolePolicy" -ForegroundColor Green

# Attach Secrets Manager policy
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

$secretsPolicy | Out-File -FilePath "secrets-policy.json" -Encoding utf8

aws iam put-role-policy `
  --role-name realestate-ecs-execution-role `
  --policy-name SecretsManagerAccess `
  --policy-document file://secrets-policy.json | Out-Null

Write-Host "  ✅ Attached Secrets Manager policy" -ForegroundColor Green

Write-Host ""

# Step 2: Create ECS Task Role
Write-Host "Step 2: Creating ECS Task Role..." -ForegroundColor Yellow

try {
    aws iam create-role `
      --role-name realestate-ecs-task-role `
      --assume-role-policy-document file://ecs-trust-policy.json `
      --description "ECS task role for realestate ETL" 2>$null | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Task role created" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Role may already exist" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Role may already exist" -ForegroundColor Yellow
}

# Attach S3 access policy
$s3Policy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::realestate-etl-data/*",
        "arn:aws:s3:::realestate-etl-data"
      ]
    }
  ]
}
"@

$s3Policy | Out-File -FilePath "s3-policy.json" -Encoding utf8

aws iam put-role-policy `
  --role-name realestate-ecs-task-role `
  --policy-name S3Access `
  --policy-document file://s3-policy.json | Out-Null

Write-Host "  ✅ Attached S3 access policy" -ForegroundColor Green

Write-Host ""

# Cleanup
Remove-Item ecs-trust-policy.json -ErrorAction SilentlyContinue
Remove-Item secrets-policy.json -ErrorAction SilentlyContinue
Remove-Item s3-policy.json -ErrorAction SilentlyContinue

Write-Host "==========================================" -ForegroundColor Green
Write-Host "IAM Roles Created!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Created Roles:" -ForegroundColor Cyan
Write-Host "  - realestate-ecs-execution-role" -ForegroundColor White
Write-Host "    ARN: arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-execution-role" -ForegroundColor Gray
Write-Host "  - realestate-ecs-task-role" -ForegroundColor White
Write-Host "    ARN: arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-task-role" -ForegroundColor Gray
Write-Host ""
Write-Host "You can now run the ECS task!" -ForegroundColor Green
