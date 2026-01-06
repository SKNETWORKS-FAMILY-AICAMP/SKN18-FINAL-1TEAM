# Fix S3 Permissions for ECS Task Role
# Usage: .\fix-s3-permissions.ps1

$ErrorActionPreference = "Stop"

Write-Host "==================================================================="
Write-Host "  ECS Task Role에 S3 읽기 권한 추가"
Write-Host "==================================================================="
Write-Host ""

$ROLE_NAME = "realestate-ecs-task-role"
$BUCKET_NAME = "realestate-etl-data"

# Check if role exists
Write-Host "Checking if role exists..."
$roleExists = aws iam get-role --role-name $ROLE_NAME --query 'Role.RoleName' --output text 2>$null

if (-not $roleExists) {
    Write-Host "Error: Role '$ROLE_NAME' not found"
    Write-Host "Please create the role first using create-iam-roles.ps1"
    exit 1
}

Write-Host "  ✓ Role exists: $ROLE_NAME"
Write-Host ""

# Create S3 read policy
Write-Host "Creating S3 read policy..."

$policyDocument = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::$BUCKET_NAME",
                "arn:aws:s3:::$BUCKET_NAME/*"
            ]
        }
    ]
}
"@

$policyFile = Join-Path $PSScriptRoot "temp-s3-policy.json"
$policyDocument | Out-File -FilePath $policyFile -Encoding utf8

# Attach inline policy to role
Write-Host "Attaching S3 policy to role..."
aws iam put-role-policy `
    --role-name $ROLE_NAME `
    --policy-name "S3ReadAccess" `
    --policy-document "file://$policyFile"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ S3 policy attached successfully"
} else {
    Write-Host "  ✗ Failed to attach policy"
    Remove-Item $policyFile -ErrorAction SilentlyContinue
    exit 1
}

# Clean up
Remove-Item $policyFile -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==================================================================="
Write-Host "✅ S3 권한 설정 완료!"
Write-Host "==================================================================="
Write-Host ""
Write-Host "다음 단계:"
Write-Host "  1. ETL Pipeline 실행: .\run-full-aws-pipeline.ps1"
Write-Host "  2. 또는 Import만 실행: .\run-aws-import.ps1"
Write-Host ""
