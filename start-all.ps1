# 童科绘项目一键启动脚本
# 在 PowerShell 中运行此脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  童科绘 - 项目启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/4] 检查 Python..." -ForegroundColor Yellow
try {
    python --version | Out-Null
    Write-Host "✓ Python 已安装" -ForegroundColor Green
} catch {
    Write-Host "✗ 未找到 Python，请先安装 Python" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查 Node.js
Write-Host "[2/4] 检查 Node.js..." -ForegroundColor Yellow
try {
    node --version | Out-Null
    Write-Host "✓ Node.js 已安装" -ForegroundColor Green
} catch {
    Write-Host "✗ 未找到 Node.js，请先安装 Node.js" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动说明：" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "你需要打开两个终端窗口："
Write-Host ""
Write-Host "终端 1 - 启动后端：" -ForegroundColor Yellow
Write-Host "  cd E:\童科绘"
Write-Host "  python main.py"
Write-Host ""
Write-Host "终端 2 - 启动前端：" -ForegroundColor Yellow
Write-Host "  cd E:\童科绘\tk-frontend"
Write-Host "  npm run dev"
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$choice = Read-Host "是否现在打开两个终端窗口？(Y/N)"

if ($choice -eq "Y" -or $choice -eq "y") {
    # 启动后端
    Write-Host "正在打开后端终端..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd E:\童科绘; Write-Host '后端启动中...'; python main.py"

    # 等待一下再启动前端
    Start-Sleep -Seconds 2

    # 启动前端
    Write-Host "正在打开前端终端..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd E:\童科绘\tk-frontend; Write-Host '前端启动中...'; npm run dev"

    Write-Host ""
    Write-Host "✓ 两个终端窗口已打开！" -ForegroundColor Green
    Write-Host ""
    Write-Host "等待服务启动后，在浏览器中访问：" -ForegroundColor Cyan
    Write-Host "  http://localhost:5173" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "好的，请手动打开两个终端窗口并按照上面的说明启动。" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "按回车键退出..."
Read-Host | Out-Null
