# Fix IAM Role Trust Relationships for ECS

Write-Host "Fixing IAM Role Trust Relationships..." -ForegroundColor Cyan
Write-Host ""

# Correct trust policy for ECS tasks
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

# Update ECS Execution Role
Write-Host "Updating realestate-ecs-execution-role..." -ForegroundColor Yellow
$ecsTrustPolicy | Out-File -FilePath "ecs-trust-policy.json" -Encoding utf8

aws iam update-assume-role-policy `
  --role-name realestate-ecs-execution-role `
  --policy-document file://ecs-trust-policy.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Execution role trust policy updated" -ForegroundColor Green
} else {
    Write-Host "  ❌ Failed to update execution role" -ForegroundColor Red
}

Write-Host ""

# Update ECS Task Role
Write-Host "Updating realestate-ecs-task-role..." -ForegroundColor Yellow

aws iam update-assume-role-policy `
  --role-name realestate-ecs-task-role `
  --policy-document file://ecs-trust-policy.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Task role trust policy updated" -ForegroundColor Green
} else {
    Write-Host "  ❌ Failed to update task role" -ForegroundColor Red
}

Write-Host ""

# Cleanup
Remove-Item ecs-trust-policy.json -ErrorAction SilentlyContinue

Write-Host "==========================================" -ForegroundColor Green
Write-Host "IAM Roles Fixed!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run the ECS task:" -ForegroundColor Cyan
Write-Host "  aws ecs run-task --cluster realestate-etl-cluster --task-definition realestate-etl-task --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[subnet-0d88da4dbe1be58fe],securityGroups=[sg-0b2bdef4bce788976],assignPublicIp=ENABLED}' --region ap-northeast-2" -ForegroundColor Gray
