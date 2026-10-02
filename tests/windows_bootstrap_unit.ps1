# Pure helper checks: mock download bytes, never run them or modify the registry.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $root 'scripts/python-bootstrap.ps1')
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('teacher-helper-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
function Assert($Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Expect-Failure([scriptblock]$Action, [string]$Pattern) {
    $failed = $false
    try { & $Action | Out-Null } catch { $failed = $true; Assert ($_.Exception.Message -match $Pattern) ('Unexpected error: ' + $_.Exception.Message) }
    Assert $failed ('Expected failure: ' + $Pattern)
}
$oldArchitecture = $env:PROCESSOR_ARCHITECTURE
$oldWow = $env:PROCESSOR_ARCHITEW6432
try {
    $env:PROCESSOR_ARCHITECTURE = 'AMD64'
    Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue
    $data = Join-Path $testRoot 'consent'
    Expect-Failure { Install-TeacherPython $root $data } 'PYTHON_INSTALL_CONSENT_REQUIRED'
    Assert (-not (Test-Path -LiteralPath $data)) 'Refused consent wrote data'
    $script:called = 0
    function Invoke-WebRequest { param($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec); $script:called++; [IO.File]::WriteAllText($OutFile, 'wrong archive fixture') }
    $data = Join-Path $testRoot 'hash mismatch'
    Expect-Failure { Install-TeacherPython $root $data -AllowPythonInstall } 'UV_HASH_MISMATCH'
    Assert ($script:called -eq 1) 'Download fixture was not called exactly once'
    Assert (-not (Test-Path -LiteralPath (Join-Path $data 'managed-python/python'))) 'Unverified archive was installed'
    Assert (@(Get-ChildItem -LiteralPath (Join-Path $data 'managed-python') -Filter 'download-*').Count -eq 0) 'Temporary download was not cleaned up'
    $sentinel = Join-Path $data 'keep.txt'; [IO.File]::WriteAllText($sentinel, 'user')
    Expect-Failure { Install-TeacherPython $root $data -AllowPythonInstall } 'UV_HASH_MISMATCH'
    Assert ([IO.File]::ReadAllText($sentinel) -eq 'user') 'Retry damaged user files'
    function Invoke-WebRequest { param($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec); throw 'network-denied-fixture' }
    Expect-Failure { Install-TeacherPython $root (Join-Path $testRoot 'network') -AllowPythonInstall } 'network-denied-fixture'
    $foreign = Join-Path $testRoot 'foreign'
    New-Item -ItemType Directory -Path (Join-Path $foreign 'managed-python') | Out-Null
    Expect-Failure { Install-TeacherPython $root $foreign -AllowPythonInstall } 'Existing unmanaged'
    $bad = Join-Path $testRoot 'invalid config'; New-Item -ItemType Directory -Path $bad | Out-Null
    $config = Join-Path $bad 'runtime.json'; [IO.File]::WriteAllText($config, '{"version":1,"python":"missing"}')
    $hash = (Get-FileHash -LiteralPath $config).Hash
    Expect-Failure { Find-TeacherPython $bad $null } 'Existing runtime.json is invalid'
    Assert ((Get-FileHash -LiteralPath $config).Hash -eq $hash) 'Invalid config was changed'
    Expect-Failure { Find-TeacherPython (Join-Path $testRoot 'explicit') '/missing/python' } 'existing absolute Python 3.12'
    Expect-Failure { Assert-TeacherSeparatePaths $root (Join-Path $root 'forbidden-data') (Join-Path $testRoot 'work') } 'must not overlap'
    'PASS: consent, bad hash, network failure, retry preservation, foreign folder, invalid config, explicit bad Python, code boundary'
} finally {
    $env:PROCESSOR_ARCHITECTURE = $oldArchitecture
    $env:PROCESSOR_ARCHITEW6432 = $oldWow
    Remove-Item -LiteralPath $testRoot -Recurse -Force
}
