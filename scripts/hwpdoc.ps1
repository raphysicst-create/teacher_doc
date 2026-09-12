$ErrorActionPreference = 'Stop'
$taskPython = 'C:\Users\22\AppData\Local\Programs\Python\Python312\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw "Required Python312 not found: $taskPython" }
& $taskPython -X utf8 (Join-Path $PSScriptRoot 'hwpdoc.py') @args
exit $LASTEXITCODE
