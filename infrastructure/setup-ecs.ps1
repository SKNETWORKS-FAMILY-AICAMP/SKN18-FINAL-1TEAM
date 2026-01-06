# Phase 4: ECS Cluster and Task Definition Setup

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Phase 4: ECS Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$AWS_ACCOUNT_ID = "940075378738"
$AWS_REGION = "ap-northeast-2"
$CLUSTER_NAME = "realestate-etl-cluster"
$LOG_GROUP_NAME = "/ecs/realestate-etl"

# Step 1: Create ECS Cluster
Write-Host "Step 1: Creating ECS Cluster..." -ForegroundColor Yellow
try {
    aws ecs create-cluster `
      --cluster-name $CLUSTER_NAME `
      --region $AWS_REGION 2>$null | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ ECS Cluster created: $CLUSTER_NAME" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Cluster may already exist" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Cluster may already exist" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Create CloudWatch Log Group
Write-Host "Step 2: Creating CloudWatch Log Group..." -ForegroundColor Yellow
try {
    aws logs create-log-group `
      --log-group-name $LOG_GROUP_NAME `
      --region $AWS_REGION 2>$null | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Log Group created: $LOG_GROUP_NAME" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Log Group may already exist" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Log Group may already exist" -ForegroundColor Yellow
}

Write-Host ""

# Step 3: Get Secrets Manager ARNs
Write-Host "Step 3: Getting Secrets Manager ARNs..." -ForegroundColor Yellow
$POSTGRES_SECRET_ARN = (aws secretsmanager describe-secret --secret-id realestate/postgres --query ARN --output text)
$NEO4J_SECRET_ARN = (aws secretsmanager describe-secret --secret-id realestate/neo4j --query ARN --output text)
$ES_SECRET_ARN = (aws secretsmanager describe-secret --secret-id realestate/elasticsearch --query ARN --output text)

Write-Host "  PostgreSQL Secret: $POSTGRES_SECRET_ARN" -ForegroundColor Green
Write-Host "  Neo4j Secret: $NEO4J_SECRET_ARN" -ForegroundColor Green
Write-Host "  Elasticsearch Secret: $ES_SECRET_ARN" -ForegroundColor Green

Write-Host ""

# Step 4: Create Task Definition JSON
Write-Host "Step 4: Creating Task Definition..." -ForegroundColor Yellow

$taskDefinition = @{
    family = "realestate-etl-task"
    networkMode = "awsvpc"
    requiresCompatibilities = @("FARGATE")
    cpu = "4096"
    memory = "16384"
    executionRoleArn = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-execution-role"
    taskRoleArn = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-task-role"
    containerDefinitions = @(
        @{
            name = "etl-container"
            image = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/realestate-scripts:latest"
            essential = $true
            command = @(
                "python", "-u", "/app/scripts/run_etl_pipeline.py"
            )
            environment = @(
                @{ name = "AWS_DEFAULT_REGION"; value = $AWS_REGION }
                @{ name = "TZ"; value = "Asia/Seoul" }
            )
            secrets = @(
                @{ name = "POSTGRES_HOST"; valueFrom = "${POSTGRES_SECRET_ARN}:host::" }
                @{ name = "POSTGRES_PORT"; valueFrom = "${POSTGRES_SECRET_ARN}:port::" }
                @{ name = "POSTGRES_DB"; valueFrom = "${POSTGRES_SECRET_ARN}:database::" }
                @{ name = "POSTGRES_USER"; valueFrom = "${POSTGRES_SECRET_ARN}:username::" }
                @{ name = "POSTGRES_PASSWORD"; valueFrom = "${POSTGRES_SECRET_ARN}:password::" }
                @{ name = "NEO4J_URI"; valueFrom = "${NEO4J_SECRET_ARN}:uri::" }
                @{ name = "NEO4J_USER"; valueFrom = "${NEO4J_SECRET_ARN}:username::" }
                @{ name = "NEO4J_PASSWORD"; valueFrom = "${NEO4J_SECRET_ARN}:password::" }
                @{ name = "ES_HOST"; valueFrom = "${ES_SECRET_ARN}:host::" }
                @{ name = "ES_PORT"; valueFrom = "${ES_SECRET_ARN}:port::" }
            )
            logConfiguration = @{
                logDriver = "awslogs"
                options = @{
                    "awslogs-group" = $LOG_GROUP_NAME
                    "awslogs-region" = $AWS_REGION
                    "awslogs-stream-prefix" = "ecs"
                }
            }
        }
    )
} | ConvertTo-Json -Depth 10

$taskDefinition | Out-File -FilePath "task-definition.json" -Encoding utf8

Write-Host "  ✅ Task definition saved to: task-definition.json" -ForegroundColor Green

Write-Host ""

# Step 5: Register Task Definition
Write-Host "Step 5: Registering Task Definition..." -ForegroundColor Yellow
$registerResult = aws ecs register-task-definition --cli-input-json file://task-definition.json --region $AWS_REGION 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Task definition registered successfully" -ForegroundColor Green
} else {
    Write-Host "  ❌ Task definition registration failed" -ForegroundColor Red
    Write-Host "  Error: $registerResult" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Phase 4 Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Created Resources:" -ForegroundColor Cyan
Write-Host "  - ECS Cluster: $CLUSTER_NAME" -ForegroundColor White
Write-Host "  - CloudWatch Log Group: $LOG_GROUP_NAME" -ForegroundColor White
Write-Host "  - Task Definition: realestate-etl-task" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Test ECS task manually" -ForegroundColor White
Write-Host "2. Setup EventBridge schedule (Phase 5)" -ForegroundColor White
