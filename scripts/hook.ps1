param([Parameter(Mandatory=$true)][ValidateSet('pre','post','stop')][string]$Event)
# Windows PowerShell otherwise emits localized bootstrap errors in the console
# code page, while app hook readers decode UTF-8.
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'runtime.ps1')
    $taskPython = Get-HwpdocPython
    $taskName = @{ pre='protect_files.py'; post='audit_log.py'; stop='stop_validator.py' }[$Event]
    $taskHook = Join-Path (Split-Path $PSScriptRoot -Parent) ('.claude/hooks/' + $taskName)
    # Standard input is inherited unchanged. Preserve deny/failed exit codes.
    & $taskPython -B -X utf8 $taskHook
    exit $LASTEXITCODE
} catch {
    $taskMessage = 'hwpdoc hook unavailable; protection unverified: ' + $_.Exception.Message
    [Console]::Error.WriteLine($taskMessage)
    if ($Event -eq 'pre') { exit 2 }
    @{ systemMessage=$taskMessage } | ConvertTo-Json -Compress
    exit 0
}
