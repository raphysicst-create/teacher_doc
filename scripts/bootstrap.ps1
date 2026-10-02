[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Workspace,
    [string]$DataDir,
    [string]$Python,
    [ValidateSet('xml', 'full')][string]$Mode = 'xml',
    [switch]$SchoolData,
    [switch]$Visual
)
$ErrorActionPreference = 'Stop'
try {
    if (-not $Python) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            $Python = (& py -3.12 -c 'import sys; print(sys.executable)' 2>$null | Select-Object -Last 1)
            if ($LASTEXITCODE -ne 0) { $Python = $null }
        }
        if (-not $Python) {
            . (Join-Path $PSScriptRoot 'runtime.ps1')
            $Python = Get-HwpdocPython
        }
    }
    $arguments = @('-B', '-X', 'utf8', (Join-Path $PSScriptRoot 'bootstrap.py'), '--workspace', $Workspace, '--mode', $Mode)
    if ($DataDir) { $arguments += @('--data-dir', $DataDir) }
    if ($SchoolData) { $arguments += '--school-data' }
    if ($Visual) { $arguments += '--visual' }
    & $Python @arguments
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine('teacher_doc setup failed: ' + $_.Exception.Message + '. Use an existing Python 3.12 executable with -Python. No security settings were changed.')
    exit 2
}
