param(
    [string]$ProfilePath = "profile.yml"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# 这个启动脚本只负责切到项目目录并调用医院详情主脚本。
py hospital_hxq_start.py --profile $ProfilePath
