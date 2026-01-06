# Phase 5-6: EventBridge Scheduling Setup

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Phase 5-6: EventBridge Scheduling" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$AWS_ACCOUNT_ID = "940075378738"
$AWS_REGION = "ap-northeast-2"
$CLUSTER_NAME = "realestate-etl-cluster"
$TASK_DEFINITION = "realestate-etl-task"
$VPC_ID = "vpc-0edc6bd52bea8f771"
$SG_ID = "sg-0b2bdef4bce788976"

# Get subnet IDs
Write-Host "Getting subnet IDs..." -ForegroundColor Yellow
$SUBNETS = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].[SubnetId,Tags[?Key=='Name'].Value|[0]]" --output json | ConvertFrom-Json)
$PUBLIC_SUBNET_1 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-public-1" })[0]
$PUBLIC_SUBNET_2 = ($SUBNETS | Where-Object { $_[1] -eq "realestate-public-2" })[0]

Write-Host "  Public Subnet 1: $PUBLIC_SUBNET_1" -ForegroundColor Green
Write-Host "  Public Subnet 2: $PUBLIC_SUBNET_2" -ForegroundColor Green
Write-Host ""

# Step 1: Create SNS Topic
Write-Host "Step 1: Creating SNS Topic..." -ForegroundColor Yellow
try {
    $SNS_TOPIC_ARN = (aws sns create-topic --name realestate-etl-notifications --region $AWS_REGION --query TopicArn --output text)
    Write-Host "  ✅ SNS Topic created: $SNS_TOPIC_ARN" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Topic may already exist" -ForegroundColor Yellow
    $SNS_TOPIC_ARN = (aws sns list-topics --region $AWS_REGION --query "Topics[?contains(TopicArn, 'realestate-etl-notifications')].TopicArn" --output text)
}

Write-Host ""

# Step 2: Create EventBridge IAM Role
Write-Host "Step 2: Creating EventBridge IAM Role..." -ForegroundColor Yellow

$trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@

$trustPolicy | Out-File -FilePath "eventbridge-trust-policy.json" -Encoding utf8

try {
    aws iam create-role `
      --role-name realestate-eventbridge-role `
      --assume-role-policy-document file://eventbridge-trust-policy.json 2>$null | Out-Null
    Write-Host "  ✅ EventBridge role created" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Role may already exist" -ForegroundColor Yellow
}

# Attach ECS task execution policy
$ecsPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask"
      ],
      "Resource": "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:task-definition/${TASK_DEFINITION}:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-execution-role",
        "arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-ecs-task-role"
      ]
    }
  ]
}
"@

$ecsPolicy | Out-File -FilePath "eventbridge-ecs-policy.json" -Encoding utf8

aws iam put-role-policy `
  --role-name realestate-eventbridge-role `
  --policy-name ECSTaskExecution `
  --policy-document file://eventbridge-ecs-policy.json | Out-Null

$EVENTBRIDGE_ROLE_ARN = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/realestate-eventbridge-role"
Write-Host "  ✅ EventBridge role configured: $EVENTBRIDGE_ROLE_ARN" -ForegroundColor Green

Write-Host ""

# Step 3: Create EventBridge Rule
Write-Host "Step 3: Creating EventBridge Rule..." -ForegroundColor Yellow
Write-Host "  Schedule: Daily at 12:00 PM KST (03:00 UTC)" -ForegroundColor Cyan

# Create rule (cron: 0 3 * * ? = 03:00 UTC = 12:00 PM KST)
aws events put-rule `
  --name realestate-etl-daily `
  --description "Run ETL pipeline daily at 12:00 PM KST" `
  --schedule-expression "cron(0 3 * * ? *)" `
  --state ENABLED `
  --region $AWS_REGION | Out-Null

Write-Host "  ✅ EventBridge rule created: realestate-etl-daily" -ForegroundColor Green

Write-Host ""

# Step 4: Add ECS Target to Rule
Write-Host "Step 4: Adding ECS target to EventBridge rule..." -ForegroundColor Yellow

$ecsTarget = @"
[
  {
    "Id": "1",
    "Arn": "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:cluster/${CLUSTER_NAME}",
    "RoleArn": "${EVENTBRIDGE_ROLE_ARN}",
    "EcsParameters": {
      "TaskDefinitionArn": "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:task-definition/${TASK_DEFINITION}",
      "TaskCount": 1,
      "LaunchType": "FARGATE",
      "NetworkConfiguration": {
        "awsvpcConfiguration": {
          "Subnets": ["${PUBLIC_SUBNET_1}", "${PUBLIC_SUBNET_2}"],
          "SecurityGroups": ["${SG_ID}"],
          "AssignPublicIp": "ENABLED"
        }
      }
    }
  }
]
"@

$ecsTarget | Out-File -FilePath "eventbridge-targets.json" -Encoding utf8

# Add target using absolute path
$absolutePath = (Resolve-Path "eventbridge-targets.json").Path
aws events put-targets `
  --rule realestate-etl-daily `
  --targets file://$absolutePath `
  --region $AWS_REGION | Out-Null

Write-Host "  ✅ ECS target added to EventBridge rule" -ForegroundColor Green

Write-Host ""

# Cleanup temp files
Remove-Item eventbridge-trust-policy.json -ErrorAction SilentlyContinue
Remove-Item eventbridge-ecs-policy.json -ErrorAction SilentlyContinue
Remove-Item eventbridge-targets.json -ErrorAction SilentlyContinue

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Phase 5-6 Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "EventBridge Scheduler Configured:" -ForegroundColor Cyan
Write-Host "  Rule: realestate-etl-daily" -ForegroundColor White
Write-Host "  Schedule: Daily at 12:00 PM KST (03:00 UTC)" -ForegroundColor White
Write-Host "  Target: ECS Task (${TASK_DEFINITION})" -ForegroundColor White
Write-Host "  Cluster: ${CLUSTER_NAME}" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Test manual ECS task execution" -ForegroundColor White
Write-Host "2. Monitor CloudWatch logs" -ForegroundColor White
Write-Host "3. Verify database updates" -ForegroundColor White
Write-Host ""
Write-Host "To manually trigger the task:" -ForegroundColor Cyan
Write-Host "  aws ecs run-task --cluster ${CLUSTER_NAME} --task-definition ${TASK_DEFINITION} --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[${PUBLIC_SUBNET_1}],securityGroups=[${SG_ID}],assignPublicIp=ENABLED}' --region ${AWS_REGION}" -ForegroundColor Gray
