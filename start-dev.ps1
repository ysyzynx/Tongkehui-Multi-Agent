param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "SilentlyContinue"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendRoot = Join-Path $ProjectRoot "tk-frontend"

function Stop-PortProcess {
    param([int]$Port)

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($item in $listeners) {
        if ($item.OwningProcess -and $item.OwningProcess -ne 0) {
            Stop-Process -Id $item.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "[1/4] Cleaning ports..."
Stop-PortProcess -Port $BackendPort
Stop-PortProcess -Port $FrontendPort

Write-Host "[2/4] Starting backend on port $BackendPort..."
$backendCmd = "Set-Location '$ProjectRoot'; python -m uvicorn main:app --reload --host 0.0.0.0 --port $BackendPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null

Write-Host "[3/4] Starting frontend on port $FrontendPort..."
$frontendCmd = "Set-Location '$FrontendRoot'; npm run dev -- --host 0.0.0.0 --port $FrontendPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd | Out-Null

Start-Sleep -Seconds 2

Write-Host "[4/4] Opening browser pages..."
Start-Process "http://localhost:$FrontendPort"
Start-Process "http://localhost:$BackendPort/docs"

Write-Host "Done."
Write-Host "Frontend: http://localhost:$FrontendPort"
Write-Host "Backend docs: http://localhost:$BackendPort/docs"
