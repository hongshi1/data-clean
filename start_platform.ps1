# -*- coding: utf-8 -*-
"""一键启动: 后端(带密码) + 公网隧道 + 打开浏览器
用法: powershell -ExecutionPolicy Bypass -File start_platform.ps1
停止: 双击 stop_platform.ps1 或直接关闭 cloudflared/python 进程
"""
$ErrorActionPreference = "SilentlyContinue"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

$PASSWORD = "srs-2026-graph"   # 公网访问密码, 改这里

Write-Host "== SRS上下文关联图谱平台 一键启动 ==" -ForegroundColor Cyan

# 0. 清理旧进程
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match "server\\main" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1

# 1. 后端(带密码)
$env:ACCESS_TOKEN = $PASSWORD
Start-Process -FilePath "python" -ArgumentList "-X","utf8","server\main.py" `
  -WorkingDirectory $ROOT -WindowStyle Hidden
Write-Host "[1/3] 后端启动中..." -ForegroundColor Green
Start-Sleep 4

# 2. 公网隧道
$cfLog = Join-Path $ROOT "tools\bin\cf-tunnel.log"
Start-Process -FilePath (Join-Path $ROOT "tools\bin\cloudflared.exe") `
  -ArgumentList "tunnel","--url","http://127.0.0.1:8300" `
  -WorkingDirectory $ROOT -WindowStyle Hidden `
  -RedirectStandardError $cfLog
Write-Host "[2/3] 公网隧道建立中..." -ForegroundColor Green
Start-Sleep 8

# 3. 提取链接并打开
$url = ""
try {
  $log = Get-Content $cfLog -Raw -ErrorAction SilentlyContinue
  $m = [regex]::Match($log, "https://[a-z0-9-]+\.trycloudflare\.com")
  $url = $m.Value
} catch {}
Start-Process "http://127.0.0.1:8300"

Write-Host "[3/3] 完成!" -ForegroundColor Green
Write-Host ""
Write-Host "  本地访问: http://127.0.0.1:8300" -ForegroundColor Yellow
if ($url) { Write-Host "  公网访问: $url  (密码: $PASSWORD)" -ForegroundColor Yellow }
else { Write-Host "  公网链接稍后查看: tools\bin\cf-tunnel.log" -ForegroundColor DarkGray }
Write-Host ""
Write-Host "  停止服务: 运行 stop_platform.ps1" -ForegroundColor DarkGray
Write-Host "  (注意: 公网链接每次重启会变; 军事SRS数据, 演示完建议关闭)" -ForegroundColor Red
