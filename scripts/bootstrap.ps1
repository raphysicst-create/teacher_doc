[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Workspace,
    [string]$DataDir,
    [string]$Python,
    [switch]$AllowPythonInstall,
    [ValidateSet('xml', 'full')][string]$Mode = 'xml',
    [ValidateSet('codex', 'claude')][string]$App = 'codex',
    [string]$SkillName = 'hwpx',
    [string]$McpUrl,
    [switch]$NoMcp,
    [switch]$SchoolData,
    [switch]$Visual
)
$ErrorActionPreference = 'Stop'
try {
    if ($NoMcp -and $PSBoundParameters.ContainsKey('McpUrl')) {
        throw '-NoMcp and -McpUrl cannot be used together.'
    }
    . (Join-Path $PSScriptRoot 'python-bootstrap.ps1')
    $root = Split-Path $PSScriptRoot -Parent
    $Workspace = [IO.Path]::GetFullPath($Workspace)
    . (Join-Path $PSScriptRoot 'runtime.ps1')
    $DataDir = Get-HwpdocData -Workspace $Workspace -DataDir $DataDir
    Assert-TeacherSeparatePaths $root $DataDir $Workspace
    $marker = Join-Path $Workspace '.hwpdoc/workspace.json'
    if (Test-Path -LiteralPath $marker) {
        $settings = Get-Content -LiteralPath $marker -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($settings.kind -ne 'hwpdoc-workspace' -or $settings.version -ne 1 -or $settings.app -ne $App) {
            throw 'Existing workspace settings are invalid or for a different app. Preserved without downloading Python.'
        }
    }
    $Python = Find-TeacherPython $DataDir $Python
    if (-not $Python) { $Python = Install-TeacherPython $root $DataDir -AllowPythonInstall:$AllowPythonInstall }
    [Console]::Error.WriteLine('Using Python 3.12: ' + $Python)
    $arguments = @('-B', '-I', '-X', 'utf8', (Join-Path $PSScriptRoot 'bootstrap.py'), '--workspace', $Workspace, '--data-dir', $DataDir, '--mode', $Mode, '--app', $App, '--skill-name', $SkillName)
    if ($SchoolData) { $arguments += '--school-data' }
    if ($Visual) { $arguments += '--visual' }
    if ($PSBoundParameters.ContainsKey('McpUrl')) { $arguments += @('--mcp-url', $McpUrl) }
    if ($NoMcp) { $arguments += '--no-mcp' }
    & $Python @arguments
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine('teacher_doc setup failed: ' + $_.Exception.Message + ' Existing data and security settings were preserved.')
    exit 2
}
