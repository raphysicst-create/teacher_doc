$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime.ps1')
$taskPython = Get-HwpdocPython
& $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'hwpdoc.py') @args
exit $LASTEXITCODE
