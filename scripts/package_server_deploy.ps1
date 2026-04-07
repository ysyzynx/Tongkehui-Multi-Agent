param(
    [string]$OutputRoot = "releases"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageName = "tongkehui-server-$timestamp"
$stagingRoot = Join-Path $projectRoot $OutputRoot
$stagingDir = Join-Path $stagingRoot $packageName
$zipPath = "$stagingDir.zip"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  童科绘服务器部署打包工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $stagingRoot)) {
    New-Item -ItemType Directory -Path $stagingRoot | Out-Null
}

if (Test-Path $stagingDir) {
    Write-Host "[清理] 删除旧的打包目录..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $stagingDir
}
if (Test-Path $zipPath) {
    Write-Host "[清理] 删除旧的压缩包..." -ForegroundColor Yellow
    Remove-Item -Force $zipPath
}

Write-Host "[创建] 建立打包目录..." -ForegroundColor Green
New-Item -ItemType Directory -Path $stagingDir | Out-Null
New-Item -ItemType Directory -Path (Join-Path $stagingDir "deploy") | Out-Null

# ========================================
# 1. 复制后端文件
# ========================================
Write-Host "[1/4] 复制后端文件..." -ForegroundColor Green

$backendFiles = @("main.py", "requirements.txt", "README.md")
foreach ($file in $backendFiles) {
    $src = Join-Path $projectRoot $file
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $stagingDir $file) -Force
    }
}

$backendDirs = @("config", "models", "router", "agent", "prompts", "utils", "docs", "article")
$excludeDirs = @(".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build")
$excludeFiles = @("*.pyc", "*.pyo", "*.log", "*.db-shm", "*.db-wal", "*.db")

foreach ($dir in $backendDirs) {
    $srcDir = Join-Path $projectRoot $dir
    if (-not (Test-Path $srcDir)) { continue }

    $dstDir = Join-Path $stagingDir $dir
    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

    $robocopyArgs = @("`"$srcDir`"", "`"$dstDir`"", "/E", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP")
    if ($excludeDirs.Count -gt 0) { $robocopyArgs += "/XD"; $robocopyArgs += $excludeDirs }
    if ($excludeFiles.Count -gt 0) { $robocopyArgs += "/XF"; $robocopyArgs += $excludeFiles }

    & robocopy @robocopyArgs | Out-Null
}

# ========================================
# 2. 复制前端
# ========================================
Write-Host "[2/4] 复制前端源代码..." -ForegroundColor Green
$frontendRoot = Join-Path $projectRoot "tk-frontend"
$dstFrontend = Join-Path $stagingDir "tk-frontend"
New-Item -ItemType Directory -Force -Path $dstFrontend | Out-Null

$robocopyArgs = @("`"$frontendRoot`"", "`"$dstFrontend`"", "/E", "/R:1", "/W:1")
$robocopyArgs += "/XD"; $robocopyArgs += $excludeDirs
& robocopy @robocopyArgs | Out-Null

# ========================================
# 3. 创建部署配置
# ========================================
Write-Host "[3/4] 创建部署配置文件..." -ForegroundColor Green

# .env.production
$envProd = @"
# 童科绘生产环境配置
DB_URL=sqlite:///./data/tongkehui.db
HOST=0.0.0.0
PORT=8000
DEBUG=False
CORS_ORIGINS=http://localhost,http://localhost:3000,http://localhost:8080

# LLM (阿里云 DashScope)
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-turbo
VISION_MODEL=qwen-vl-max

# DeepSearch
DEEPSEARCH_API_KEY=your_api_key_here
DEEPSEARCH_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
DEEPSEARCH_MODEL=qwen3-max
DEEPSEARCH_ENABLE_SEARCH=True
DEEPSEARCH_SELF_CHECK=True

# 火山引擎图像
VOLCENGINE_API_KEY=your_api_key_here
VOLCENGINE_IMAGE_MODEL=doubao-seedream-5-0-260128

# SerpAPI
SERPAPI_API_KEY=
"@
Set-Content -Path (Join-Path $stagingDir ".env.production") -Value $envProd -Encoding UTF8

# nginx.conf
$nginxConf = @"
upstream tongkehui_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    location / {
        root /opt/tongkehui/frontend-dist;
        try_files \$uri \$uri/ /index.html;
        expires 30d;
    }

    location /api/ {
        proxy_pass http://tongkehui_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /docs {
        proxy_pass http://tongkehui_backend;
    }

    location /openapi.json {
        proxy_pass http://tongkehui_backend;
    }

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript;
}
"@
Set-Content -Path (Join-Path $stagingDir "deploy/nginx.conf") -Value $nginxConf -Encoding UTF8

# systemd service
$systemdService = @"
[Unit]
Description=TongKeHui Backend
After=network.target

[Service]
Type=notify
User=tongkehui
Group=tongkehui
WorkingDirectory=/opt/tongkehui
Environment="PATH=/opt/tongkehui/.venv/bin"
ExecStart=/opt/tongkehui/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=append:/opt/tongkehui/logs/backend.log
StandardError=append:/opt/tongkehui/logs/backend-error.log

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/tongkehui

[Install]
WantedBy=multi-user.target
"@
Set-Content -Path (Join-Path $stagingDir "deploy/tongkehui.service") -Value $systemdService -Encoding UTF8

# 简单的部署说明
$readme = @"
# 童科绘服务器部署

## 快速开始（Linux）

```bash
# 1. 解压并进入目录
tar -xzf tongkehui-server-$timestamp.tar.gz
cd tongkehui-server-$timestamp

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.production .env
nano .env  # 填入你的 API keys

# 5. 创建数据目录
mkdir -p data logs

# 6. 启动后端（测试）
uvicorn main:app --host 0.0.0.0 --port 8000

# 7. 构建前端（新终端）
cd tk-frontend
npm install
npm run build
# 将 dist 目录复制到 ../frontend-dist
cp -r dist ../frontend-dist
```

## 生产部署建议

1. 使用 Nginx 作为反向代理（配置见 deploy/nginx.conf）
2. 使用 systemd 管理服务（配置见 deploy/tongkehui.service）
3. 配置 HTTPS（Let's Encrypt）
4. 定期备份数据库

## 访问地址

- 前端：http://your-server/
- 后端 API：http://your-server/api/
- API 文档：http://your-server/docs

## 需要配置的 API Keys

- OPENAI_API_KEY（阿里云 DashScope）
- DEEPSEARCH_API_KEY（阿里云 DashScope）
- VOLCENGINE_API_KEY（火山引擎，可选）
"@
Set-Content -Path (Join-Path $stagingDir "DEPLOY.md") -Value $readme -Encoding UTF8

# ========================================
# 4. 打包
# ========================================
Write-Host "[4/4] 创建压缩包..." -ForegroundColor Green
Compress-Archive -Path "$stagingDir\*" -DestinationPath $zipPath -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  打包完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "打包目录: $stagingDir"
Write-Host "压缩包: $zipPath"
Write-Host ""
Write-Host "部署说明请查看: $stagingDir\DEPLOY.md"
