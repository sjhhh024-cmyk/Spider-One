param()

$ErrorActionPreference = "Stop"

$PythonExe = "F:\Anaconda3\envs\spider\python.exe"
$SshExe = "ssh.exe"
$TunnelLocalPort = 6379
$TunnelRemoteAddress = "localhost:6379"
$TunnelServer = "root@8.140.197.200"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartScript = Join-Path $ProjectRoot "doctor_ywbd\start.py"
$TunnelForward = "$TunnelLocalPort`:$TunnelRemoteAddress"
$TunnelCommandLine = "$SshExe -N -L $TunnelForward $TunnelServer"


function Test-TunnelProcess {
    $sshProcesses = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "ssh.exe" -and
        $_.CommandLine -like "*-L $TunnelForward*" -and
        $_.CommandLine -like "*$TunnelServer*"
    }

    return [bool]$sshProcesses
}


function Start-TunnelProcess {
    if (Test-TunnelProcess) {
        Write-Host "SSH 隧道已存在，无需重复启动。"
        return
    }

    Write-Host "开始启动 SSH 隧道: $TunnelCommandLine"
    Start-Process -FilePath $SshExe -ArgumentList @("-N", "-L", $TunnelForward, $TunnelServer) | Out-Null
    Start-Sleep -Seconds 3

    if (-not (Test-TunnelProcess)) {
        throw "SSH 隧道启动失败，请先手工执行：$TunnelCommandLine"
    }

    Write-Host "SSH 隧道启动成功，本地 Redis 端口: $TunnelLocalPort"
}


function Start-SpiderProject {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "找不到 Python 解释器，请先修改 start.ps1 里的 `$PythonExe。当前值：$PythonExe"
    }

    if (-not (Test-Path -LiteralPath $StartScript)) {
        throw "找不到启动文件：$StartScript"
    }

    Write-Host "开始运行 YWBD 项目: $StartScript"
    & $PythonExe $StartScript
}


Start-TunnelProcess
Start-SpiderProject
