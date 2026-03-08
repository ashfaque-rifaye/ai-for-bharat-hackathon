# VaaniSetu MCP Server Setup Script
# Run this once to install uv and pre-cache all AWS MCP servers

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VaaniSetu MCP Server Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check and install uv
Write-Host "[1/3] Checking uv installation..." -ForegroundColor Yellow
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "  uv not found. Installing..." -ForegroundColor Yellow
    irm https://astral.sh/uv/install.ps1 | iex
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvCmd) {
        Write-Host "  ERROR: uv installation failed. Please install manually:" -ForegroundColor Red
        Write-Host "  https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Red
        exit 1
    }
    Write-Host "  uv installed successfully!" -ForegroundColor Green
} else {
    Write-Host "  uv found: $(uv version)" -ForegroundColor Green
}

# Step 2: Install Python 3.10+ via uv (required by AWS MCP servers)
Write-Host ""
Write-Host "[2/3] Ensuring Python 3.10+ is available..." -ForegroundColor Yellow
uv python install 3.12 2>$null
Write-Host "  Python ready." -ForegroundColor Green

# Step 3: Pre-cache AWS MCP servers (speeds up first launch)
Write-Host ""
Write-Host "[3/3] Pre-caching AWS MCP servers..." -ForegroundColor Yellow

$servers = @(
    "awslabs.core-mcp-server",
    "awslabs.aws-documentation-mcp-server",
    "awslabs.iac-mcp-server",
    "awslabs.dynamodb-mcp-server",
    "awslabs.bedrock-kb-retrieval-mcp-server",
    "awslabs.amazon-sns-sqs-mcp-server",
    "awslabs.aws-serverless-mcp-server",
    "awslabs.cost-explorer-mcp-server",
    "awslabs.aws-diagram-mcp-server",
    "awslabs.cloudwatch-mcp-server"
)

$total = $servers.Count
$current = 0

foreach ($server in $servers) {
    $current++
    Write-Host "  [$current/$total] Caching $server..." -ForegroundColor Gray -NoNewline
    try {
        uv tool install "$server@latest" --force 2>$null
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " SKIP (will download on first use)" -ForegroundColor Yellow
    }
}

# Step 4: Verify AWS credentials
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verifying AWS Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$awsCmd = Get-Command aws -ErrorAction SilentlyContinue
if ($awsCmd) {
    Write-Host "  AWS CLI found." -ForegroundColor Green
    try {
        $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
        if ($identity) {
            Write-Host "  Account: $($identity.Account)" -ForegroundColor Green
            Write-Host "  Region:  ap-south-1 (Mumbai)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  WARNING: AWS credentials not configured." -ForegroundColor Yellow
        Write-Host "  Run: aws configure" -ForegroundColor Yellow
    }
} else {
    Write-Host "  WARNING: AWS CLI not installed." -ForegroundColor Yellow
    Write-Host "  Install: https://aws.amazon.com/cli/" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "MCP Servers configured in .vscode/mcp.json:" -ForegroundColor White
Write-Host "  - aws-core           : Intelligent planning & orchestration" -ForegroundColor Gray
Write-Host "  - aws-documentation  : AWS docs (Connect, Bedrock, Polly, etc.)" -ForegroundColor Gray
Write-Host "  - aws-iac            : CDK best practices & CloudFormation" -ForegroundColor Gray
Write-Host "  - aws-dynamodb       : DynamoDB design guidance & operations" -ForegroundColor Gray
Write-Host "  - aws-bedrock-kb     : Bedrock Knowledge Bases retrieval" -ForegroundColor Gray
Write-Host "  - aws-sns-sqs        : SNS/SQS messaging (SMS notifications)" -ForegroundColor Gray
Write-Host "  - aws-serverless     : Lambda/SAM serverless development" -ForegroundColor Gray
Write-Host "  - aws-cost-explorer  : Cost tracking ($100 budget)" -ForegroundColor Gray
Write-Host "  - aws-diagram        : Architecture diagram generation" -ForegroundColor Gray
Write-Host "  - aws-cloudwatch     : Metrics, logs & monitoring" -ForegroundColor Gray
Write-Host "  - context7           : Up-to-date library documentation" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Restart VS Code to activate MCP servers" -ForegroundColor Yellow
Write-Host "  2. Check MCP server status in VS Code (Ctrl+Shift+P > 'MCP')" -ForegroundColor Yellow
Write-Host "  3. Configure AWS credentials: aws configure --region ap-south-1" -ForegroundColor Yellow
Write-Host ""
