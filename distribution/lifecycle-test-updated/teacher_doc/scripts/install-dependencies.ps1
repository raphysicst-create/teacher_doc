param([string]$Python, [string]$DataDir, [switch]$SchoolData, [switch]$Visual)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime.ps1')
if (-not $Python) { $Python = Get-HwpdocPython }
if (-not $DataDir) { $DataDir = if ($env:HWPDOC_PC_DATA) { $env:HWPDOC_PC_DATA } else { Join-Path $env:LOCALAPPDATA 'hwpdoc' } }
$DataDir = [IO.Path]::GetFullPath($DataDir)
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskFlavor = 'base'
if ($SchoolData) { $taskFlavor += '-school' }
if ($Visual) { $taskFlavor += '-visual' }
$taskVenv = Join-Path $DataDir ('runtimes/0.1.0-' + $taskFlavor)
if (Test-Path -LiteralPath $taskVenv) { throw 'Environment already exists; inspect it before selecting or replacing it.' }
if ($Visual) {
    Write-Host 'Visual dependency: PyMuPDF uses free AGPL-3.0. See LICENSE, NOTICE.md and SOURCE.md in the release.'
}
& $Python -X utf8 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 2)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 required' }
& $Python -X utf8 -m venv $taskVenv
if ($LASTEXITCODE -ne 0) { throw 'venv creation failed; partial environment preserved for diagnosis' }
$taskExecutable = Join-Path $taskVenv 'Scripts/python.exe'
$taskRequirements = @('requirements-base.txt', 'requirements-windows.txt')
if ($SchoolData) { $taskRequirements += 'requirements-school-data.txt' }
if ($Visual) { $taskRequirements += 'requirements-visual.txt' }
foreach ($taskFile in $taskRequirements) {
    & $taskExecutable -X utf8 -m pip install --disable-pip-version-check -r (Join-Path $taskRoot ('distribution/' + $taskFile))
    if ($LASTEXITCODE -ne 0) { throw ('Dependency install failed: ' + $taskFile + '; existing runtime settings unchanged') }
}
& $taskExecutable -X utf8 -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed; existing runtime settings unchanged' }
$taskConfig = Join-Path $DataDir 'runtime.json'
$taskRecord = @{version=1; python=$taskExecutable} | ConvertTo-Json
if (Test-Path -LiteralPath $taskConfig) {
    $taskConfig = Join-Path $taskVenv 'runtime-to-select.json'
    Write-Host 'Existing runtime preserved. Review runtime-to-select.json before switching environments.'
}
[IO.File]::WriteAllText($taskConfig, $taskRecord, [Text.UTF8Encoding]::new($false))
Write-Host ('Environment ready: ' + $taskVenv + '. Run doctor from the teacher workspace; Hancom/app integration is not verified by pip.')
