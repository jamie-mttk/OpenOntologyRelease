# Requires Windows PowerShell 5.1+
param()

$ServiceName = 'OpenOntology'
$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
$Jsl = Join-Path $Root 'jsl64.exe'
$JslDir = $Root

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal $id
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Wait-Key {
    Write-Host ''
    Write-Host 'Press Enter to close this window. / 按 Enter 关闭此窗口...'
    try { [void](Read-Host) } catch { Start-Sleep -Seconds 8 }
}

if (-not (Test-IsAdmin)) {
    $ps = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $elevArgs = @(
        '-NoLogo',
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', $MyInvocation.MyCommand.Path
    )
    try {
        Start-Process -FilePath $ps -Verb RunAs -WorkingDirectory $Root -ArgumentList $elevArgs | Out-Null
    } catch {
        Write-Host '[ERROR] Elevation cancelled or failed. / UAC 被取消或提权失败。'
        Wait-Key
        exit 1
    }
    exit 0
}

Set-Location -LiteralPath $Root

if (-not (Test-Path -LiteralPath $Jsl)) {
    Write-Host "[ERROR] Not found: $Jsl"
    Wait-Key
    exit 1
}

Write-Host "Uninstalling Windows service: $ServiceName"
Write-Host "正在卸载 Windows 服务: $ServiceName"
Write-Host ''

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -ne 'Stopped') {
    Write-Host "Stopping service $ServiceName ..."
    Write-Host "正在停止服务 $ServiceName ..."
    try {
        Stop-Service -Name $ServiceName -Force -ErrorAction Stop
        Start-Sleep -Seconds 2
    } catch {
        Write-Host "[WARN] Stop service: $($_.Exception.Message)"
    }
    Write-Host ''
}

$proc = Start-Process -FilePath $Jsl -ArgumentList '-remove' -WorkingDirectory $JslDir -Wait -PassThru
$code = 0
if ($null -ne $proc -and $null -ne $proc.ExitCode) { $code = [int]$proc.ExitCode }

Start-Sleep -Seconds 1
$left = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

Write-Host ''
if ($null -eq $left) {
    Write-Host '[OK] Service uninstalled successfully.'
    Write-Host '服务卸载成功。'
    Write-Host "Service name: $ServiceName"
    Write-Host "服务名: $ServiceName"
    Wait-Key
    exit 0
}

Write-Host "[FAILED] Service uninstall failed. exitcode=$code"
Write-Host '服务卸载失败（服务仍存在）。'
Write-Host "Service name: $ServiceName"
Write-Host "服务名: $ServiceName"
Wait-Key
exit 1
