# Public teacher_doc entry point; existing hwpdoc callers remain compatible.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime.ps1')
$taskPython = Get-HwpdocPython
& $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'teacher_doc.py') @args
exit $LASTEXITCODE
