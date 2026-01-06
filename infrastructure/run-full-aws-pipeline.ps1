# Run Full AWS Pipeline
# Usage: .\run-full-aws-pipeline.ps1

param(
    [switch]$SkipUpload = $false,
    [switch]$SkipImport = $false
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

Write-Host ("=" * 70)
Write-Host "  AWS Full Pipeline Execution"
Write-Host ("=" * 70)

$startTime = Get-Date

# 1. Upload to S3
if (-not $SkipUpload) {
    Write-Host ""
    Write-Host "[1/2] Uploading data to S3..."
    .\upload-data-to-s3.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Upload failed"
        exit 1
    }
}

# 2. Run Import
if (-not $SkipImport) {
    Write-Host ""
    Write-Host "[2/2] Running import..."
    .\run-aws-import.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Import failed"
        exit 1
    }
}

$elapsed = (Get-Date) - $startTime

Write-Host ""
Write-Host ("=" * 70)
Write-Host "Pipeline execution completed!"
Write-Host "Elapsed time: $($elapsed.ToString('hh\:mm\:ss'))"
Write-Host ("=" * 70)
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Check PostgreSQL: psql -h <RDS_ENDPOINT> -U postgres -d realestate"
Write-Host "  2. CloudWatch Logs: aws logs tail /ecs/realestate-crawler --follow"
Write-Host "  3. Check S3: aws s3 ls s3://$env:S3_BUCKET/data/ --recursive"
