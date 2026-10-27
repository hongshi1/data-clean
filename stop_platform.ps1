# 停止平台: 关闭后端与公网隧道
$ErrorActionPreference = "SilentlyContinue"
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match "server\\main" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "已停止: 后端 + 公网隧道" -ForegroundColor Green
