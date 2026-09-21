$ErrorActionPreference = 'Stop'
$taskModule = Join-Path (Split-Path -Parent $PSScriptRoot) 'schoolinfo-mcp'
$taskNodeMajor = [int]((& node --version) -replace '^v(\d+).*$', '$1')
if ($taskNodeMajor -lt 22) { throw 'schoolinfo-mcp requires Node.js 22 or later.' }
Push-Location -LiteralPath $taskModule
try {
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'schoolinfo dependency installation failed.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'schoolinfo build failed.' }
} finally {
    Pop-Location
}
