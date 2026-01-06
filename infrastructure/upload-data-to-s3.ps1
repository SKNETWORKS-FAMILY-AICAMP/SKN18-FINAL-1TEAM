# Upload local data to S3 bucket
# Usage: .\upload-data-to-s3.ps1

param(
    [string]$BucketName,
    [string]$DataDir = "c:\dev\SKN18-FINAL-1TEAM\data"
)

# Load environment variables from aws-resources.env
$envFile = Join-Path $PSScriptRoot "aws-resources.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^export\s+S3_BUCKET="?([^"]+)"?') {
            $BucketName = $matches[1]
        }
    }
}

# Use default bucket name if not found
if (-not $BucketName) {
    $BucketName = "realestate-etl-data"
    Write-Host "Warning: S3 bucket name not found, using default: $BucketName"
}

Write-Host ("=" * 70)
Write-Host "  Upload Local Data to S3"
Write-Host ("=" * 70)
Write-Host "Bucket: $BucketName"
Write-Host "Data Directory: $DataDir"
Write-Host ""

# Check if data directory exists
if (-not (Test-Path $DataDir)) {
    Write-Host "Error: Data directory does not exist: $DataDir"
    exit 1
}

# Directories to upload
$UPLOAD_DIRS = @(
    "RDB/land",
    "GraphDB_data",
    "actual_transaction_price",
    "brokerInfo"
)

foreach ($dir in $UPLOAD_DIRS) {
    $localPath = Join-Path $DataDir $dir
    
    if (Test-Path $localPath) {
        Write-Host "Uploading: $dir"
        
        # S3 sync command (only upload changed files)
        aws s3 sync $localPath "s3://$BucketName/data/$dir" `
            --exclude "*.pyc" `
            --exclude "__pycache__/*" `
            --exclude ".DS_Store"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Completed: $dir"
        } else {
            Write-Host "  [FAILED] $dir"
        }
    } else {
        Write-Host "  [SKIP] Directory not found: $dir"
    }
}

Write-Host ""
Write-Host ("=" * 70)
Write-Host "S3 Upload Complete!"
Write-Host ("=" * 70)

# Show uploaded file statistics
Write-Host ""
Write-Host "Uploaded File Statistics:"
aws s3 ls s3://$BucketName/data/ --recursive --summarize | Select-Object -Last 2
