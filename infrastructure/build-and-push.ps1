# Phase 3: Docker Image Build and ECR Push Script

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Phase 3: Docker Image Preparation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Change to project root
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot
Write-Host "Working directory: $projectRoot" -ForegroundColor Gray
Write-Host ""

# Get AWS Account ID
$AWS_ACCOUNT_ID = "940075378738"  # Hardcoded to avoid JSON parsing issues
$AWS_REGION = "ap-northeast-2"
$ECR_REPO_NAME = "realestate-scripts"
$ECR_URI = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

Write-Host "AWS Account ID: $AWS_ACCOUNT_ID" -ForegroundColor Green
Write-Host "ECR URI: $ECR_URI" -ForegroundColor Green
Write-Host ""

# Step 1: Create ECR Repository
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Step 1: Creating ECR Repository" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

try {
    $ecrResult = aws ecr create-repository `
      --repository-name $ECR_REPO_NAME `
      --image-scanning-configuration scanOnPush=true `
      --region $AWS_REGION 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ ECR repository created: $ECR_REPO_NAME" -ForegroundColor Green
    } else {
        if ($ecrResult -like "*RepositoryAlreadyExistsException*") {
            Write-Host "  ⚠️  Repository already exists" -ForegroundColor Yellow
        } else {
            Write-Host "  ❌ Error: $ecrResult" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "  ⚠️  Repository may already exist" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: ECR Login
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Step 2: Logging into ECR" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$loginCommand = aws ecr get-login-password --region $AWS_REGION
if ($loginCommand) {
    $loginCommand | docker login --username AWS --password-stdin "$ECR_URI" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ ECR login successful" -ForegroundColor Green
    } else {
        Write-Host "  ❌ ECR login failed" -ForegroundColor Red
        Write-Host "  Make sure Docker Desktop is running" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "  ❌ Failed to get ECR login password" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Check Dockerfile
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Step 3: Checking Dockerfile" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$dockerfilePath = "infra\docker\scripts.Dockerfile"
if (Test-Path $dockerfilePath) {
    Write-Host "  ✅ Dockerfile found: $dockerfilePath" -ForegroundColor Green
} else {
    Write-Host "  ❌ Dockerfile not found: $dockerfilePath" -ForegroundColor Red
    Write-Host "  Please create Dockerfile first" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 4: Build Docker Image
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Step 4: Building Docker Image" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  This may take 5-10 minutes..." -ForegroundColor Yellow
Write-Host ""

$imageName = "${ECR_URI}/${ECR_REPO_NAME}:latest"

docker build -f $dockerfilePath -t $ECR_REPO_NAME:latest . 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  ✅ Docker image built successfully" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  ❌ Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 5: Tag Image
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Step 5: Tagging Image for ECR" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

docker tag ${ECR_REPO_NAME}:latest $imageName

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Image tagged: $imageName" -ForegroundColor Green
} else {
    Write-Host "  ❌ Image tagging failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 6: Push to ECR
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Step 6: Pushing Image to ECR" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  This may take 5-10 minutes..." -ForegroundColor Yellow
Write-Host ""

docker push $imageName 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "  ✅ Image pushed to ECR successfully" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  ❌ Image push failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Phase 3 Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ECR Repository: $ECR_REPO_NAME" -ForegroundColor Cyan
Write-Host "Image URI: $imageName" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Create ECS Cluster" -ForegroundColor White
Write-Host "2. Create ECS Task Definition" -ForegroundColor White
Write-Host "3. Setup EventBridge Schedule" -ForegroundColor White

# Save ECR info
$ecrInfo = @"
=== ECR Information ===

Repository Name: $ECR_REPO_NAME
Repository URI: ${ECR_URI}/${ECR_REPO_NAME}
Image URI: $imageName
Region: $AWS_REGION

Docker Commands:
  Login: aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI
  Pull: docker pull $imageName
  Build: docker build -f $dockerfilePath -t $ECR_REPO_NAME:latest .
  Push: docker push $imageName
"@

$ecrInfo | Out-File -FilePath "ecr-info.txt" -Encoding utf8
Write-Host ""
Write-Host "ECR info saved to: ecr-info.txt" -ForegroundColor Cyan
