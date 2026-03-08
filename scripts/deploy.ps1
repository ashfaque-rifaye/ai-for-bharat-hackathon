# VaaniSetu — Full Deployment Script
# Deploys infrastructure, seeds data, and sets up Bedrock Agent
#
# Usage: .\scripts\deploy.ps1 [-SkipFrontend] [-SkipAgent] [-StacksOnly]

param(
    [switch]$SkipFrontend,
    [switch]$SkipAgent,
    [switch]$StacksOnly,
    [string]$Region = "us-east-1",
    [string]$Profile = "default"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  VaaniSetu Deployment" -ForegroundColor Cyan
Write-Host "  Region: $Region" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ── Pre-flight checks ────────────────────────────────────────────────
Write-Host "[0/6] Pre-flight checks..." -ForegroundColor Yellow

# Check AWS CLI
$awsCmd = Get-Command aws -ErrorAction SilentlyContinue
if (-not $awsCmd) {
    Write-Host "  ERROR: AWS CLI not found. Install from https://aws.amazon.com/cli/" -ForegroundColor Red
    exit 1
}

# Check CDK
$cdkCmd = Get-Command cdk -ErrorAction SilentlyContinue
if (-not $cdkCmd) {
    Write-Host "  CDK not found. Installing..." -ForegroundColor Yellow
    npm install -g aws-cdk
}

# Check Python
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Host "  ERROR: Python not found" -ForegroundColor Red
    exit 1
}

# Verify AWS credentials
try {
    $identity = aws sts get-caller-identity --profile $Profile 2>$null | ConvertFrom-Json
    Write-Host "  AWS Account: $($identity.Account)" -ForegroundColor Green
    Write-Host "  IAM User: $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: AWS credentials not configured. Run 'aws configure'" -ForegroundColor Red
    exit 1
}

# ── Step 1: Install CDK dependencies ─────────────────────────────────
Write-Host ""
Write-Host "[1/6] Installing CDK dependencies..." -ForegroundColor Yellow
Push-Location "$ProjectRoot\infrastructure\cdk"

if (-not (Test-Path "venv")) {
    python -m venv venv
}

& ".\venv\Scripts\Activate.ps1"
pip install -r requirements.txt --quiet
Write-Host "  CDK dependencies installed" -ForegroundColor Green
Pop-Location

# ── Step 2: CDK Bootstrap (first time only) ──────────────────────────
Write-Host ""
Write-Host "[2/6] CDK Bootstrap..." -ForegroundColor Yellow
Push-Location "$ProjectRoot\infrastructure\cdk"

try {
    cdk bootstrap "aws://$($identity.Account)/$Region" --profile $Profile 2>$null
    Write-Host "  CDK bootstrapped" -ForegroundColor Green
} catch {
    Write-Host "  CDK already bootstrapped (or error — check manually)" -ForegroundColor Yellow
}

Pop-Location

# ── Step 3: Deploy CDK Stacks ────────────────────────────────────────
Write-Host ""
Write-Host "[3/6] Deploying CDK stacks..." -ForegroundColor Yellow
Push-Location "$ProjectRoot\infrastructure\cdk"

$stacks = @("VaaniSetu-Data", "VaaniSetu-AI", "VaaniSetu-API", "VaaniSetu-Connect")

foreach ($stack in $stacks) {
    Write-Host "  Deploying $stack..." -ForegroundColor Gray
    try {
        cdk deploy $stack --require-approval never --profile $Profile 2>&1 | ForEach-Object {
            if ($_ -match "Outputs|✅|Stack ARN") { Write-Host "    $_" -ForegroundColor Green }
        }
        Write-Host "  ✅ $stack deployed" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ $stack failed: $_" -ForegroundColor Red
        if ($stack -eq "VaaniSetu-Connect") {
            Write-Host "    Note: Connect stack may require manual instance creation first" -ForegroundColor Yellow
        }
    }
}

Pop-Location

if ($StacksOnly) {
    Write-Host ""
    Write-Host "Stacks deployed. Exiting (StacksOnly mode)." -ForegroundColor Cyan
    exit 0
}

# ── Step 4: Seed scheme data ─────────────────────────────────────────
Write-Host ""
Write-Host "[4/6] Seeding scheme data..." -ForegroundColor Yellow

try {
    python "$ProjectRoot\scripts\seed_data.py" --region $Region
    Write-Host "  ✅ Scheme data seeded (10 schemes)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Seed data failed: $_" -ForegroundColor Red
}

# ── Step 5: Setup Bedrock Agent ──────────────────────────────────────
if (-not $SkipAgent) {
    Write-Host ""
    Write-Host "[5/6] Setting up Bedrock Agent..." -ForegroundColor Yellow

    try {
        python "$ProjectRoot\scripts\setup_bedrock_agent.py" --region $Region
        Write-Host "  ✅ Bedrock Agent configured" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ Agent setup failed: $_" -ForegroundColor Red
        Write-Host "    You can retry: python scripts\setup_bedrock_agent.py" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[5/6] Skipping Bedrock Agent setup (--SkipAgent)" -ForegroundColor Yellow
}

# ── Step 6: Build & Deploy Frontend ─────────────────────────────────
if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "[6/6] Building frontend..." -ForegroundColor Yellow
    Push-Location "$ProjectRoot\frontend"

    # Get API URLs from CloudFormation outputs
    try {
        $outputs = aws cloudformation describe-stacks --stack-name VaaniSetu-API --region $Region --profile $Profile 2>$null | ConvertFrom-Json
        $restUrl = ($outputs.Stacks[0].Outputs | Where-Object { $_.OutputKey -eq "RestAPIUrl" }).OutputValue
        $wsUrl = ($outputs.Stacks[0].Outputs | Where-Object { $_.OutputKey -eq "WebSocketUrl" }).OutputValue

        # Write .env for frontend
        @"
VITE_API_URL=$restUrl
VITE_WS_URL=$wsUrl
VITE_APP_NAME=VaaniSetu
"@ | Set-Content ".env.production"

        Write-Host "  API URL: $restUrl" -ForegroundColor Gray
        Write-Host "  WS URL: $wsUrl" -ForegroundColor Gray
    } catch {
        Write-Host "  Warning: Could not get API URLs from CloudFormation" -ForegroundColor Yellow
    }

    npm install --silent
    npm run build
    Write-Host "  ✅ Frontend built (dist/)" -ForegroundColor Green
    Write-Host "  Note: Deploy dist/ to S3+CloudFront or Amplify" -ForegroundColor Gray

    Pop-Location
} else {
    Write-Host ""
    Write-Host "[6/6] Skipping frontend build (--SkipFrontend)" -ForegroundColor Yellow
}

# ── Summary ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# Get stack outputs
try {
    $apiOutputs = aws cloudformation describe-stacks --stack-name VaaniSetu-API --region $Region --profile $Profile 2>$null | ConvertFrom-Json
    foreach ($output in $apiOutputs.Stacks[0].Outputs) {
        Write-Host "  $($output.OutputKey): $($output.OutputValue)" -ForegroundColor Gray
    }
} catch {}

Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    1. Claim a phone number in Amazon Connect console" -ForegroundColor Yellow
Write-Host "    2. Assign VaaniSetu-MainFlow contact flow to the number" -ForegroundColor Yellow
Write-Host "    3. Test: Call the number and say 'मुझे योजना चाहिए'" -ForegroundColor Yellow
Write-Host "    4. Web: Open frontend dist/index.html or deploy to Amplify" -ForegroundColor Yellow
Write-Host ""
