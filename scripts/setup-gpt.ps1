# Reconnect a single canonical skill and register project-local event adapters.
# This does not trust hooks or claim either app loaded them.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = 'C:/Users/USER/AppData/Local/Programs/Python/Python312/python.exe'
$taskCanonical = Join-Path $taskRoot '.claude/skills/hwpx'
$taskLink = Join-Path $taskRoot '.agents/skills/hwpx'
New-Item -ItemType Directory -Force (Split-Path -Parent $taskLink) | Out-Null
if (Test-Path -LiteralPath $taskLink) {
    $taskExisting = Get-Item -LiteralPath $taskLink -Force
    if ($taskExisting.LinkType -notin @('Junction','SymbolicLink') -or
        [IO.Path]::GetFullPath($taskExisting.Target[0]) -ne [IO.Path]::GetFullPath($taskCanonical)) {
        throw "Existing discovery path differs; preserved: $taskLink"
    }
} else {
    New-Item -ItemType Junction -Path $taskLink -Target $taskCanonical | Out-Null
}
$taskHooks = @{}
foreach ($taskEvent in @('PreToolUse','PostToolUse','Stop')) {
    $taskScript = switch ($taskEvent) { 'PreToolUse' {'protect_files.py'} 'PostToolUse' {'audit_log.py'} 'Stop' {'stop_validator.py'} }
    $taskScriptPath = (Join-Path $taskRoot ".claude/hooks/$taskScript").Replace('\','/')
    # Paths currently contain no spaces. Explicit PowerShell entrypoint handles moved paths too.
    $taskCommand = "powershell.exe -NoProfile -NonInteractive -Command `"& '$taskPython' -X utf8 '$taskScriptPath'; exit `$LASTEXITCODE`""
    $taskHandler = @{type='command'; command=$taskCommand; timeout=10}
    if ($taskEvent -eq 'Stop') { $taskHandler.timeout = 120 }
    $taskGroup = @{hooks=@($taskHandler)}
    if ($taskEvent -ne 'Stop') { $taskGroup.matcher = 'Bash|apply_patch|Edit|Write|mcp__kordoc__.*' }
    $taskHooks[$taskEvent] = @($taskGroup)
}
$taskConfig = @{description='teacher_doc adapters. Host trust and integration verification required.'; hooks=$taskHooks} | ConvertTo-Json -Depth 10
$taskHookPath = Join-Path $taskRoot '.codex/hooks.json'
if (Test-Path -LiteralPath $taskHookPath) {
    # Do not overwrite a foreign or hand-edited hook registration.
    $taskCurrent = Get-Content -LiteralPath $taskHookPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($taskCurrent.description -notin @('teacher_doc adapters. Host trust and integration verification required.', 'Hwp_doc adapters. Host trust and integration verification required.')) {
        throw "Existing hooks preserved; merge explicitly: $taskHookPath"
    }
    $taskCurrentNormalized = $taskCurrent | ConvertTo-Json -Depth 10 -Compress
    $taskWantedNormalized = $taskConfig | ConvertFrom-Json | ConvertTo-Json -Depth 10 -Compress
    if ($taskCurrentNormalized -ne $taskWantedNormalized) {
        # Object order can differ without changing definitions: preserve the file
        # instead of risking replacement of an added user hook.
        Write-Output "Existing hook registration preserved: $taskHookPath"
        & $taskPython -X utf8 (Join-Path $PSScriptRoot 'gpt_environment.py') inventory
        exit $LASTEXITCODE
    }
}
[IO.File]::WriteAllText($taskHookPath, $taskConfig + "`n", (New-Object Text.UTF8Encoding $false))
& $taskPython -X utf8 (Join-Path $PSScriptRoot 'gpt_environment.py') inventory
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output 'Link/config prepared. Review /hooks; actual loading and blocking remain separate checks.'
