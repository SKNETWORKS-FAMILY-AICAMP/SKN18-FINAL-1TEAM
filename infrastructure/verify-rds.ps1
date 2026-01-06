# RDS PostgreSQL 설정 확인 스크립트

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "RDS PostgreSQL 설정 확인" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# RDS 인스턴스 확인
Write-Host "1. RDS 인스턴스 상태 확인..." -ForegroundColor Yellow
$rdsInfo = (aws rds describe-db-instances --db-instance-identifier realestate-postgres --output json 2>$null | ConvertFrom-Json)

if ($rdsInfo) {
    $db = $rdsInfo.DBInstances[0]
    
    Write-Host "  ✅ RDS 인스턴스 발견!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  DB 식별자: $($db.DBInstanceIdentifier)" -ForegroundColor White
    Write-Host "  상태: $($db.DBInstanceStatus)" -ForegroundColor $(if ($db.DBInstanceStatus -eq "available") { "Green" } else { "Yellow" })
    Write-Host "  엔진: $($db.Engine) $($db.EngineVersion)" -ForegroundColor White
    Write-Host "  인스턴스 클래스: $($db.DBInstanceClass)" -ForegroundColor White
    Write-Host "  스토리지: $($db.AllocatedStorage) GB" -ForegroundColor White
    Write-Host "  퍼블릭 액세스: $($db.PubliclyAccessible)" -ForegroundColor White
    
    if ($db.Endpoint) {
        Write-Host "  엔드포인트: $($db.Endpoint.Address)" -ForegroundColor Cyan
        Write-Host "  포트: $($db.Endpoint.Port)" -ForegroundColor White
    } else {
        Write-Host "  엔드포인트: 아직 생성 중..." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "  VPC ID: $($db.DBSubnetGroup.VpcId)" -ForegroundColor White
    Write-Host "  서브넷 그룹: $($db.DBSubnetGroup.DBSubnetGroupName)" -ForegroundColor White
    Write-Host "  보안 그룹: $($db.VpcSecurityGroups[0].VpcSecurityGroupId)" -ForegroundColor White
    
} else {
    Write-Host "  ❌ RDS 인스턴스를 찾을 수 없습니다!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "2. DB 서브넷 그룹 확인..." -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan

$subnetGroup = (aws rds describe-db-subnet-groups --db-subnet-group-name realestate-db-subnet-group --output json 2>$null | ConvertFrom-Json)

if ($subnetGroup) {
    $sg = $subnetGroup.DBSubnetGroups[0]
    Write-Host "  ✅ DB 서브넷 그룹 발견!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  이름: $($sg.DBSubnetGroupName)" -ForegroundColor White
    Write-Host "  VPC: $($sg.VpcId)" -ForegroundColor White
    Write-Host "  서브넷 개수: $($sg.Subnets.Count)" -ForegroundColor White
    
    foreach ($subnet in $sg.Subnets) {
        Write-Host "    - $($subnet.SubnetIdentifier) ($($subnet.SubnetAvailabilityZone.Name))" -ForegroundColor Gray
    }
} else {
    Write-Host "  ❌ DB 서브넷 그룹을 찾을 수 없습니다!" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "설정 검증 결과" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# 검증
$issues = @()

if ($db.DBInstanceStatus -ne "available") {
    Write-Host "⏳ RDS가 아직 생성 중입니다 (현재: $($db.DBInstanceStatus))" -ForegroundColor Yellow
    Write-Host "   예상 대기 시간: 5-10분" -ForegroundColor Yellow
} else {
    Write-Host "✅ RDS 사용 가능" -ForegroundColor Green
}

if ($db.Engine -ne "postgres") {
    $issues += "엔진이 PostgreSQL이 아닙니다"
}

if ($db.DBInstanceClass -ne "db.t3.micro") {
    Write-Host "⚠️  인스턴스 클래스: $($db.DBInstanceClass) (권장: db.t3.micro)" -ForegroundColor Yellow
}

if (-not $db.PubliclyAccessible) {
    $issues += "퍼블릭 액세스가 비활성화되어 있습니다"
}

if ($db.VpcSecurityGroups[0].VpcSecurityGroupId -ne "sg-0b2bdef4bce788976") {
    Write-Host "⚠️  보안 그룹: $($db.VpcSecurityGroups[0].VpcSecurityGroupId) (권장: sg-0b2bdef4bce788976)" -ForegroundColor Yellow
}

if ($db.DBSubnetGroup.DBSubnetGroupName -ne "realestate-db-subnet-group") {
    $issues += "DB 서브넷 그룹이 올바르지 않습니다"
}

Write-Host ""
if ($issues.Count -eq 0) {
    Write-Host "🎉 모든 설정이 올바릅니다!" -ForegroundColor Green
} else {
    Write-Host "⚠️  다음 문제가 발견되었습니다:" -ForegroundColor Yellow
    foreach ($issue in $issues) {
        Write-Host "  - $issue" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "다음 단계" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if ($db.DBInstanceStatus -eq "available" -and $db.Endpoint) {
    Write-Host ""
    Write-Host "✅ RDS가 준비되었습니다!" -ForegroundColor Green
    Write-Host ""
    Write-Host "연결 정보:" -ForegroundColor Cyan
    Write-Host "  Host: $($db.Endpoint.Address)" -ForegroundColor White
    Write-Host "  Port: $($db.Endpoint.Port)" -ForegroundColor White
    Write-Host "  Database: realestate" -ForegroundColor White
    Write-Host "  Username: postgres" -ForegroundColor White
    Write-Host "  Password: RealEstate2024!Secure" -ForegroundColor White
    Write-Host ""
    Write-Host "다음 단계:" -ForegroundColor Yellow
    Write-Host "1. Secrets Manager에 자격증명 저장" -ForegroundColor White
    Write-Host "2. 연결 테스트" -ForegroundColor White
    Write-Host "3. Phase 3 진행" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "⏳ RDS 생성이 완료될 때까지 기다려주세요..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "진행 상황 확인:" -ForegroundColor Cyan
    Write-Host "  aws rds describe-db-instances --db-instance-identifier realestate-postgres --query 'DBInstances[0].DBInstanceStatus'" -ForegroundColor Gray
}
