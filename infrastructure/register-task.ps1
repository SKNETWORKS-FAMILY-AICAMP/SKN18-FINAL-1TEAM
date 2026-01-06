# Register ECS Task Definition (Windows-compatible)

Write-Host "Registering ECS Task Definition..." -ForegroundColor Cyan

# Read JSON file
$jsonContent = Get-Content -Path "task-definition.json" -Raw

# Register using stdin
$jsonContent | aws ecs register-task-definition --cli-input-json file://- --region ap-northeast-2

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Task definition registered successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Registration failed. Try manual registration:" -ForegroundColor Red
    Write-Host ""
    Write-Host "AWS Console Method:" -ForegroundColor Yellow
    Write-Host "1. Go to: https://console.aws.amazon.com/ecs/" -ForegroundColor White
    Write-Host "2. Click 'Task Definitions' → 'Create new Task Definition'" -ForegroundColor White
    Write-Host "3. Use JSON tab and paste contents from task-definition.json" -ForegroundColor White
}
