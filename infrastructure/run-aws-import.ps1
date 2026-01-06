# Run AWS Import via ECS Task
# Usage: .\run-aws-import.ps1

param(
    [switch]$DownloadFromS3 = $true,
    [switch]$ImportNeo4j = $true,
    [switch]$ImportPostgres = $true,
    [switch]$ImportElasticsearch = $false
)

# Load environment variables
$envFile = Join-Path $PSScriptRoot "aws-resources.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^export\s+(\w+)="?([^"]+)"?') {
            $name = $matches[1]
            $value = $matches[2]
            Set-Item -Path "env:$name" -Value $value
        }
    }
} else {
    Write-Host "Error: aws-resources.env file not found"
    exit 1
}

# Set S3 bucket name
if (-not $env:S3_BUCKET) {
    $env:S3_BUCKET = "realestate-etl-data"
}

$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = "ap-northeast-2"

Write-Host ("=" * 70)
Write-Host "  AWS ECS Task - Data Import"
Write-Host ("=" * 70)

# Auto-discover AWS resources if not set
if (-not $env:ECS_CLUSTER_ARN) {
    Write-Host "Discovering ECS cluster..."
    $env:ECS_CLUSTER_ARN = aws ecs list-clusters --query 'clusterArns[0]' --output text
    if ($env:ECS_CLUSTER_ARN -eq "None" -or -not $env:ECS_CLUSTER_ARN) {
        Write-Host "Error: No ECS cluster found"
        exit 1
    }
    Write-Host "  Found: $env:ECS_CLUSTER_ARN"
}

if (-not $env:PUBLIC_SUBNET_1) {
    Write-Host "Discovering public subnet..."
    $env:PUBLIC_SUBNET_1 = aws ec2 describe-subnets --filters "Name=map-public-ip-on-launch,Values=true" --query 'Subnets[0].SubnetId' --output text
    if ($env:PUBLIC_SUBNET_1 -eq "None" -or -not $env:PUBLIC_SUBNET_1) {
        Write-Host "Error: No public subnet found"
        exit 1
    }
    Write-Host "  Found: $env:PUBLIC_SUBNET_1"
}

if (-not $env:SG_ID) {
    Write-Host "Discovering security group..."
    $env:SG_ID = aws ec2 describe-security-groups --query 'SecurityGroups[0].GroupId' --output text
    if ($env:SG_ID -eq "None" -or -not $env:SG_ID) {
        Write-Host "Error: No security group found"
        exit 1
    }
    Write-Host "  Found: $env:SG_ID"
}

Write-Host ""

# Build command string
$commands = @()

if ($DownloadFromS3) {
    $commands += "python /app/scripts/download_from_s3.py"
}

# Add import command
$importArgs = @()
if ($ImportNeo4j -and -not $ImportPostgres -and -not $ImportElasticsearch) {
    $importArgs += "--only neo4j"
} elseif ($ImportPostgres -and -not $ImportNeo4j -and -not $ImportElasticsearch) {
    $importArgs += "--only postgres"
} elseif ($ImportElasticsearch -and -not $ImportNeo4j -and -not $ImportPostgres) {
    $importArgs += "--only es"
}

$commands += "python scripts/03_import/import_all.py $($importArgs -join ' ')"


# Combine commands
$commandString = $commands -join " && "

Write-Host "Command: $commandString"
Write-Host ""

# Extract cluster name from ARN (format: arn:aws:ecs:region:account:cluster/name)
$clusterName = $env:ECS_CLUSTER_ARN
if ($clusterName -match 'cluster/(.+)$') {
    $clusterName = $matches[1]
}

# Discover task definition (get the latest one)
Write-Host "Discovering task definition..."
$allTaskDefs = aws ecs list-task-definitions --sort DESC --query 'taskDefinitionArns' --output json | ConvertFrom-Json
if (-not $allTaskDefs -or $allTaskDefs.Count -eq 0) {
    Write-Host "Error: No task definition found"
    Write-Host "Please create a task definition first or check existing ones with:"
    Write-Host "  aws ecs list-task-definitions"
    exit 1
}
$taskDef = $allTaskDefs[0]

# Extract task definition family and revision
if ($taskDef -match 'task-definition/(.+)$') {
    $taskDefName = $matches[1]
} else {
    $taskDefName = $taskDef
}

Write-Host "  Found: $taskDefName"
Write-Host ""

# Get container name from task definition
Write-Host "Getting container name from task definition..."
$containerName = aws ecs describe-task-definition --task-definition $taskDefName --query 'taskDefinition.containerDefinitions[0].name' --output text
if (-not $containerName -or $containerName -eq "None") {
    Write-Host "Error: Could not get container name from task definition"
    exit 1
}
Write-Host "  Container: $containerName"
Write-Host ""

Write-Host "Using ECS Cluster: $clusterName"
Write-Host "Using Task Definition: $taskDefName"
Write-Host "Using Container: $containerName"
Write-Host "Using Subnet: $env:PUBLIC_SUBNET_1"
Write-Host "Using Security Group: $env:SG_ID"
Write-Host ""

# Create overrides JSON file
$overridesJson = @{
    containerOverrides = @(
        @{
            name = $containerName
            command = @("sh", "-c", $commandString)
            environment = @(
                @{
                    name = "S3_BUCKET"
                    value = $env:S3_BUCKET
                }
            )
        }
    )
} | ConvertTo-Json -Depth 10

$overridesFile = Join-Path $PSScriptRoot "task-overrides.json"
[System.IO.File]::WriteAllText($overridesFile, $overridesJson, [System.Text.Encoding]::ASCII)

Write-Host "Task overrides created: $overridesFile"
Write-Host ""

# Run ECS Task
$taskArn = aws ecs run-task `
    --cluster $clusterName `
    --task-definition $taskDefName `
    --launch-type FARGATE `
    --network-configuration "awsvpcConfiguration={subnets=[$env:PUBLIC_SUBNET_1],securityGroups=[$env:SG_ID],assignPublicIp=ENABLED}" `
    --overrides "file://$overridesFile" `
    --query 'tasks[0].taskArn' `
    --output text

# Clean up temp file
Remove-Item $overridesFile -ErrorAction SilentlyContinue

if (-not $taskArn) {
    Write-Host "Error: Failed to start ECS task"
    exit 1
}

Write-Host "[OK] Task started"
Write-Host "Task ARN: $taskArn"
Write-Host ""

# Monitor task status
Write-Host "Monitoring task status..."
Write-Host "(Press Ctrl+C to stop monitoring, task will continue running)"
Write-Host ""

$maxWaitMinutes = 30
$startTime = Get-Date

while ($true) {
    $elapsed = (Get-Date) - $startTime
    
    if ($elapsed.TotalMinutes -gt $maxWaitMinutes) {
        Write-Host ""
        Write-Host "Max wait time ($maxWaitMinutes minutes) exceeded"
        Write-Host "Task is still running. Check CloudWatch Logs:"
        Write-Host "  aws logs tail /ecs/realestate-crawler --follow"
        break
    }
    
    $status = aws ecs describe-tasks `
        --cluster $clusterName `
        --tasks $taskArn `
        --query 'tasks[0].lastStatus' `
        --output text
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] Task status: $status"
    
    if ($status -eq "STOPPED") {
        # Check exit code
        $exitCode = aws ecs describe-tasks `
            --cluster $clusterName `
            --tasks $taskArn `
            --query 'tasks[0].containers[0].exitCode' `
            --output text
        
        Write-Host ""
        if ($exitCode -eq "0") {
            Write-Host "[SUCCESS] Task completed successfully!"
        } else {
            Write-Host "[FAILED] Task failed (Exit Code: $exitCode)"
            
            # Get failure reason
            $reason = aws ecs describe-tasks `
                --cluster $clusterName `
                --tasks $taskArn `
                --query 'tasks[0].stoppedReason' `
                --output text
            
            Write-Host "Reason: $reason"
        }
        break
    }
    
    Start-Sleep -Seconds 10
}

Write-Host ""
Write-Host ("=" * 70)
Write-Host "CloudWatch Logs:"
Write-Host "  aws logs tail /ecs/realestate-crawler --follow"
Write-Host ("=" * 70)
