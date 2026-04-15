param()

$ErrorActionPreference = "Stop"

$PythonExe = "F:\Anaconda3\envs\spider\python.exe"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartScript = Join-Path $ProjectRoot "doctor_wygk\start.py"


function Start-SpiderProject {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "找不到 Python 解释器，请先修改 start.ps1 里的 `$PythonExe。当前值：$PythonExe"
    }

    if (-not (Test-Path -LiteralPath $StartScript)) {
        throw "找不到启动文件：$StartScript"
    }

    Write-Host "开始运行 doctor_wygk 项目: $StartScript"
    & $PythonExe $StartScript
}


Start-SpiderProject
