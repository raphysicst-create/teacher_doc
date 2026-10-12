# A real Windows bootstrap with every supported pre-existing Python discovery
# route unavailable. Only for disposable GitHub-hosted runners, never a user PC.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$EvidenceDir)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') { throw 'This isolation fixture only runs on disposable Windows GitHub Actions runners.' }
$source = Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
function Assert($Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Invoke-Bootstrap([string]$Name, [switch]$Consent) {
    $args = @('-NoProfile', '-NonInteractive', '-File', $bootstrap, '-Workspace', $work, '-DataDir', $data)
    if ($Consent) { $args += '-AllowPythonInstall' }
    $quoted = ($args | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $process = Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList $quoted -Wait -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $EvidenceDir ($Name + '.stdout')) -RedirectStandardError (Join-Path $EvidenceDir ($Name + '.stderr'))
    return $process.ExitCode
}
function Snapshot-Registry {
    $rows = @()
    foreach ($root in @('HKCU:\Software\Python', 'HKLM:\Software\Python', 'HKLM:\Software\WOW6432Node\Python')) {
        if (Test-Path -LiteralPath $root) {
            $keys = @((Get-Item -LiteralPath $root)) + @(Get-ChildItem -LiteralPath $root -Recurse)
            foreach ($key in $keys) {
                foreach ($name in ($key.GetValueNames() | Sort-Object)) {
                    $rows += [ordered]@{ key = $key.Name; name = $name; kind = [string]$key.GetValueKind($name); value = $key.GetValue($name) }
                }
            }
        }
    }
    return (ConvertTo-Json -InputObject @($rows) -Depth 10 -Compress)
}
function Snapshot-Settings {
    return [ordered]@{ process_path = $env:PATH; user_path = [Environment]::GetEnvironmentVariable('PATH','User'); machine_path = [Environment]::GetEnvironmentVariable('PATH','Machine'); registry = (Snapshot-Registry); policy = @(Get-ExecutionPolicy -List | ForEach-Object { "$($_.Scope)=$($_.ExecutionPolicy)" }) } | ConvertTo-Json -Depth 12 -Compress
}
$temporary = Join-Path $env:RUNNER_TEMP ('teacher no python ' + [char]0xAD50 + [char]0xC0AC + ' ' + [guid]::NewGuid().ToString('N'))
$code = Join-Path $temporary ('plugin ' + [char]0xD55C + [char]0xAE00)
$cleanHome = Join-Path $temporary 'clean home'
$data = Join-Path $temporary ('PC ' + [char]0xB370 + [char]0xC774 + [char]0xD130)
$work = Join-Path $temporary ('teacher ' + [char]0xC791 + [char]0xC5C5)
New-Item -ItemType Directory -Path $code, $cleanHome | Out-Null
Get-ChildItem -LiteralPath $source -Force | Where-Object { $_.Name -ne '.git' } | Copy-Item -Destination $code -Recurse
$beforeOriginal = Snapshot-Settings
$beforeOriginal | Set-Content (Join-Path $EvidenceDir 'host-before.json') -Encoding UTF8
$renamed = @()
$oldEnv = @{}
foreach ($name in @('PATH','HOME','USERPROFILE','LOCALAPPDATA','HWPDOC_PC_DATA','PYTHONPATH','PYTHONHOME')) { $oldEnv[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
try {
    # The product code has no test-only skip-discovery switch. The runner's
    # Python registry entries are moved temporarily and restored in finally.
    foreach ($path in @('HKCU:\Software\Python', 'HKLM:\Software\Python', 'HKLM:\Software\WOW6432Node\Python')) {
        if (Test-Path -LiteralPath $path) {
            $hiddenName = 'TeacherDocCiHiddenPython_' + [guid]::NewGuid().ToString('N')
            $hidden = Join-Path (Split-Path $path -Parent) $hiddenName
            Rename-Item -LiteralPath $path -NewName $hiddenName
            $renamed += @{ original = $path; hidden = $hidden }
        }
    }
    $env:PATH = "$env:SystemRoot\System32\WindowsPowerShell\v1.0"
    $env:HOME = $cleanHome; $env:USERPROFILE = $cleanHome; $env:LOCALAPPDATA = Join-Path $cleanHome 'AppData/Local'; $env:HWPDOC_PC_DATA = $data
    Remove-Item Env:PYTHONPATH, Env:PYTHONHOME -ErrorAction SilentlyContinue
    $commands = @(Get-Command python, python3, python3.12, py, pymanager -CommandType Application -ErrorAction SilentlyContinue)
    ConvertTo-Json -InputObject @($commands | Select-Object Name, Source, CommandType) | Set-Content (Join-Path $EvidenceDir 'command-resolution.json') -Encoding UTF8
    Assert ($commands.Count -eq 0) 'Isolation failed: a Python command is still discoverable'
    . (Join-Path $code 'scripts/python-bootstrap.ps1')
    Assert (-not (Find-TeacherPython $data $null)) 'Isolation failed: product discovery found an existing Python'
    Assert (-not (Test-Path -LiteralPath $data)) 'Runtime/data already existed before first install'
    [ordered]@{ command_resolution = @($commands); discovered_python = $null; data_existed = $false; supported_discovery_isolated = $true; note = 'Hosted toolcache files can remain on disk, but PATH, per-user default folder, registry and runtime selection cannot reach them.' } | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $EvidenceDir 'no-python-baseline.json') -Encoding UTF8
    $before = Snapshot-Settings
    $before | Set-Content (Join-Path $EvidenceDir 'isolated-before.json') -Encoding UTF8
    $bootstrap = Join-Path $code 'scripts/bootstrap.ps1'
    $codeResult = Invoke-Bootstrap 'declined'
    Assert ($codeResult -eq 2) 'Missing consent did not stop with exit 2'
    Assert (-not (Test-Path -LiteralPath $data)) 'Missing consent wrote PC data'
    $codeResult = Invoke-Bootstrap 'first' -Consent
    Assert ($codeResult -eq 0) 'First install failed; inspect first.stderr'
    $summaryPath = Join-Path $work '.hwpdoc/onboarding.json'
    $summary = Get-Content -LiteralPath $summaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $receiptPath = Join-Path $data 'managed-python/install-receipt.json'
    $receipt = Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert ($summary.status -eq 'ready_xml' -and $summary.practice.status -eq 'xml_pass') 'XML/first-document verification failed'
    Assert ($summary.source_python.StartsWith((Join-Path $data 'managed-python/python'), [StringComparison]::OrdinalIgnoreCase)) 'Existing host Python silently replaced the downloaded source runtime'
    Assert ($summary.source_python_version -eq '3.12.15') 'Unexpected downloaded Python version'
    Assert ($summary.python.StartsWith((Join-Path $data 'runtimes'), [StringComparison]::OrdinalIgnoreCase)) 'Virtual environment escaped app data'
    Assert ($receipt.python -eq $summary.source_python) 'Receipt and actual runtime differ'
    $manifest = Get-Content (Join-Path $code 'distribution/python-downloads.json') -Raw | ConvertFrom-Json
    Assert ($receipt.python_sha256 -eq $manifest.($receipt.python_key).sha256) 'Receipt SHA-256 differs from pinned metadata'
    $sentinel = Join-Path $work 'keep user document.txt'
    [IO.File]::WriteAllText($sentinel, 'User content must survive reinstallation.')
    $preserve = @($sentinel, (Join-Path $work '.hwpdoc/workspace.json'), (Join-Path $data 'runtime.json'), (Join-Path $work 'output/teacher-doc-practice/first-document.hwpx'))
    $hashes = @($preserve | ForEach-Object { Get-FileHash -LiteralPath $_ -Algorithm SHA256 | Select-Object Path, Hash })
    ConvertTo-Json -InputObject $hashes | Set-Content (Join-Path $EvidenceDir 'user-files-before.json') -Encoding UTF8
    Copy-Item -LiteralPath $summaryPath -Destination (Join-Path $EvidenceDir 'first-onboarding.json')
    $codeResult = Invoke-Bootstrap 'repeat'
    Assert ($codeResult -eq 0) 'Reinstallation without a new download consent failed'
    foreach ($item in $hashes) { Assert ((Get-FileHash -LiteralPath $item.Path).Hash -eq $item.Hash) ('Existing file changed: ' + $item.Path) }
    $after = Snapshot-Settings
    $after | Set-Content (Join-Path $EvidenceDir 'isolated-after.json') -Encoding UTF8
    Assert ($before -eq $after) 'Bootstrap changed PATH, Python registry or execution policy'
    Copy-Item -LiteralPath $summaryPath, $receiptPath -Destination $EvidenceDir
    Copy-Item -LiteralPath (Join-Path $work 'output/teacher-doc-practice') -Destination (Join-Path $EvidenceDir 'practice') -Recurse
    Copy-Item -LiteralPath (Join-Path $work '.hwpdoc/doctor.json') -Destination $EvidenceDir
    & $summary.python -I -X utf8 -c 'import json,sys; print(json.dumps(dict(executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix,version=sys.version)))' | Set-Content (Join-Path $EvidenceDir 'runtime-probe.json') -Encoding UTF8
    Assert ($LASTEXITCODE -eq 0) 'Independent runtime path/version probe failed'
    ConvertTo-Json -InputObject @($preserve | ForEach-Object { Get-FileHash -LiteralPath $_ -Algorithm SHA256 | Select-Object Path, Hash }) | Set-Content (Join-Path $EvidenceDir 'user-files-after.json') -Encoding UTF8
    'PASS: genuine download from unavailable-discovery baseline, first document, idempotent retry, preserved user files, no PATH/registry/policy changes; Hancom COM not tested.' | Set-Content (Join-Path $EvidenceDir 'RESULT.txt') -Encoding UTF8
} finally {
    foreach ($name in $oldEnv.Keys) { [Environment]::SetEnvironmentVariable($name, $oldEnv[$name], 'Process') }
    foreach ($entry in $renamed) { Rename-Item -LiteralPath $entry.hidden -NewName (Split-Path $entry.original -Leaf) }
    $restored = Snapshot-Settings
    $restored | Set-Content (Join-Path $EvidenceDir 'host-restored.json') -Encoding UTF8
    Assert ($beforeOriginal -eq $restored) 'CI fixture failed to restore runner settings'
}
