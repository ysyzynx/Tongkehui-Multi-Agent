param(
    [string]$OutputRoot = "releases"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageName = "tongkehui-local-$timestamp"
$stagingRoot = Join-Path $projectRoot $OutputRoot
$stagingDir = Join-Path $stagingRoot $packageName
$zipPath = "$stagingDir.zip"

if (-not (Test-Path $stagingRoot)) {
    New-Item -ItemType Directory -Path $stagingRoot | Out-Null
}

if (Test-Path $stagingDir) {
    Remove-Item -Recurse -Force $stagingDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Path $stagingDir | Out-Null

$includeFiles = @(
    "main.py",
    "requirements.txt",
    "start-dev.ps1",
    "start-all.ps1",
    "README.md"
)

$includeDirs = @(
    "config",
    "models",
    "router",
    "agent",
    "prompts",
    "utils",
    "docs",
    "scripts",
    "tk-frontend"
)

foreach ($file in $includeFiles) {
    $src = Join-Path $projectRoot $file
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $stagingDir $file) -Force
    }
}

$commonDirExcludes = @(".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build")
$commonFileExcludes = @("*.pyc", "*.pyo", "*.log", "*.db-shm", "*.db-wal")

foreach ($dir in $includeDirs) {
    $srcDir = Join-Path $projectRoot $dir
    if (-not (Test-Path $srcDir)) {
        continue
    }

    $dstDir = Join-Path $stagingDir $dir
    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

    $robocopyArgs = @(
        "`"$srcDir`"",
        "`"$dstDir`"",
        "/E",
        "/R:1",
        "/W:1",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP"
    )

    if ($commonDirExcludes.Count -gt 0) {
        $robocopyArgs += "/XD"
        $robocopyArgs += $commonDirExcludes
    }

    if ($commonFileExcludes.Count -gt 0) {
        $robocopyArgs += "/XF"
        $robocopyArgs += $commonFileExcludes
    }

    & robocopy @robocopyArgs | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed while copying $dir (exit=$LASTEXITCODE)"
    }
}

# 生成部署专用环境变量模板（不打包真实 .env）
$envExample = @"
# ===== Basic =====
DB_URL=sqlite:///./tongkehui.db
HOST=0.0.0.0
PORT=8000
DEBUG=True
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# ===== LLM =====
OPENAI_API_KEY=
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-turbo
VISION_MODEL=qwen-vl-max

# ===== DeepSearch (optional) =====
DEEPSEARCH_API_KEY=
DEEPSEARCH_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
DEEPSEARCH_MODEL=qwen3-max
DEEPSEARCH_ENABLE_SEARCH=True
DEEPSEARCH_SELF_CHECK=True

# ===== Volcengine image (optional) =====
VOLCENGINE_API_KEY=
VOLCENGINE_IMAGE_MODEL=doubao-seedream-5-0-260128

# ===== SerpAPI (optional) =====
SERPAPI_API_KEY=
"@
Set-Content -Path (Join-Path $stagingDir ".env.example") -Value $envExample -Encoding UTF8

$deployReadme = @"
# Local Deploy Package

## 1. Structure
- backend: Python service at package root
- frontend: tk-frontend (React + Vite)

## 2. Start
Open PowerShell in package root and run:

```powershell
./scripts/start_local_deploy.ps1
```

The script will:
1. Create Python virtual env (.venv_local)
2. Install backend dependencies
3. Install frontend dependencies
4. Start backend (8000) and frontend (5173)

## 3. First-time setup
1. Copy .env.example to .env
2. Fill your API keys and runtime settings

## 4. URLs
- Frontend: http://localhost:5173
- Backend docs: http://localhost:8000/docs
"@
Set-Content -Path (Join-Path $stagingDir "LOCAL_DEPLOY_README.md") -Value $deployReadme -Encoding UTF8

$startScript = @"
param(
    [int]`$BackendPort = 8000,
    [int]`$FrontendPort = 5173
)

`$ErrorActionPreference = "Stop"
`$projectRoot = Split-Path -Parent `$PSScriptRoot
`$projectRoot = Split-Path -Parent `$projectRoot
`$frontendRoot = Join-Path `$projectRoot "tk-frontend"
`$venvPath = Join-Path `$projectRoot ".venv_local"

if (-not (Test-Path (Join-Path `$projectRoot ".env"))) {
    if (Test-Path (Join-Path `$projectRoot ".env.example")) {
        Copy-Item (Join-Path `$projectRoot ".env.example") (Join-Path `$projectRoot ".env") -Force
        Write-Host "[Hint] .env created from .env.example. Please fill in your keys." -ForegroundColor Yellow
    }
}

if (-not (Test-Path `$venvPath)) {
    Write-Host "[1/5] 创建 Python 虚拟环境..."
    python -m venv `$venvPath
}

`$pythonExe = Join-Path `$venvPath "Scripts\python.exe"
Write-Host "[2/5] 安装后端依赖..."
& `$pythonExe -m pip install --upgrade pip
& `$pythonExe -m pip install -r (Join-Path `$projectRoot "requirements.txt")

Write-Host "[3/5] 安装前端依赖..."
Set-Location `$frontendRoot
npm install

Write-Host "[4/5] 启动后端..."
`$backendCmd = "Set-Location '`$projectRoot'; & '`$pythonExe' -m uvicorn main:app --host 0.0.0.0 --port `$BackendPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", `$backendCmd | Out-Null

Write-Host "[5/5] 启动前端..."
`$frontendCmd = "Set-Location '`$frontendRoot'; npm run dev -- --host 0.0.0.0 --port `$FrontendPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", `$frontendCmd | Out-Null

Start-Sleep -Seconds 2
Start-Process "http://localhost:`$FrontendPort"
Start-Process "http://localhost:`$BackendPort/docs"
Write-Host "Done: frontend http://localhost:`$FrontendPort ; backend docs http://localhost:`$BackendPort/docs"
"@
$deployScriptPath = Join-Path $stagingDir "scripts\start_local_deploy.ps1"
$deployScriptDir = Split-Path -Parent $deployScriptPath
if (-not (Test-Path $deployScriptDir)) {
    New-Item -ItemType Directory -Path $deployScriptDir | Out-Null
}
Set-Content -Path $deployScriptPath -Value $startScript -Encoding UTF8

Compress-Archive -Path $stagingDir -DestinationPath $zipPath -Force

Write-Host "Local deploy package created: $zipPath"
