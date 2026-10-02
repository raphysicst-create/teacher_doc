# Read-only discovery and consent-gated, application-local Python installation.
# Dot-source this file. Never invoke py.exe or WindowsApps Python aliases.
function Test-TeacherPython312([string]$Candidate) {
    if (-not $Candidate -or -not (Test-Path -LiteralPath $Candidate -PathType Leaf)) { return $false }
    if ($Candidate -match '(?i)[\\/]WindowsApps[\\/]' -or [IO.Path]::GetFileName($Candidate) -match '^(?i)py(w)?\.exe$') { return $false }
    try {
        $check = & $Candidate -I -S -c 'import sys; print("teacher-python-312" if sys.version_info[:2] == (3,12) else "wrong-version")' 2>$null
        return ($LASTEXITCODE -eq 0 -and $check -eq 'teacher-python-312')
    } catch { return $false }
}

function Get-TeacherDataDir([string]$DataDir) {
    if (-not $DataDir) { $DataDir = $env:HWPDOC_PC_DATA }
    if (-not $DataDir) {
        $base = $env:LOCALAPPDATA
        if (-not $base) { $base = Join-Path $HOME 'AppData/Local' }
        $DataDir = Join-Path $base 'hwpdoc'
    }
    return [IO.Path]::GetFullPath($DataDir)
}

function Find-TeacherPython([string]$DataDir, [string]$Python) {
    $config = Join-Path $DataDir 'runtime.json'
    if (Test-Path -LiteralPath $config) {
        $record = Get-Content -LiteralPath $config -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($record.version -ne 1 -or -not [IO.Path]::IsPathRooted($record.python) -or -not (Test-TeacherPython312 $record.python)) {
            throw 'Existing runtime.json is invalid. Preserved; choose a separate -DataDir or repair it with permission.'
        }
        return $record.python
    }
    if ($Python) {
        if (-not [IO.Path]::IsPathRooted($Python) -or -not (Test-TeacherPython312 $Python)) { throw '-Python must be an existing absolute Python 3.12 executable path.' }
        return $Python
    }
    $candidates = @()
    # Resume a completed app-local Python download after a later pip failure.
    $managedPythons = Join-Path $DataDir 'managed-python/python'
    if (Test-Path -LiteralPath $managedPythons -PathType Container) {
        $candidates += @(Get-ChildItem -LiteralPath $managedPythons -Directory -Filter 'cpython-3.12.*' | ForEach-Object { Join-Path $_.FullName 'python.exe' })
    }
    if ($env:LOCALAPPDATA) { $candidates += Join-Path $env:LOCALAPPDATA 'Programs/Python/Python312/python.exe' }
    foreach ($key in @('HKCU:\Software\Python\PythonCore\3.12\InstallPath', 'HKLM:\Software\Python\PythonCore\3.12\InstallPath', 'HKLM:\Software\WOW6432Node\Python\PythonCore\3.12\InstallPath')) {
        if (Test-Path -LiteralPath $key) {
            $entry = Get-ItemProperty -LiteralPath $key
            if ($entry.ExecutablePath) { $candidates += $entry.ExecutablePath }
            elseif ($entry.'(default)') { $candidates += Join-Path $entry.'(default)' 'python.exe' }
        }
    }
    foreach ($name in @('python3.12.exe', 'python.exe', 'python3.exe')) {
        $candidates += @(Get-Command $name -CommandType Application -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-TeacherPython312 $candidate) { return $candidate }
    }
    return $null
}

function Assert-TeacherPlainPath([string]$Path) {
    $ancestor = [IO.Path]::GetFullPath($Path)
    while ($ancestor) {
        if (Test-Path -LiteralPath $ancestor) {
            if ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Symlink/junction install paths require a plain resolved destination. Nothing was installed.'
            }
        }
        $parent = Split-Path $ancestor -Parent
        if ($parent -eq $ancestor) { break }
        $ancestor = $parent
    }
}

function Assert-TeacherSeparatePaths([string]$Root, [string]$DataDir, [string]$Workspace) {
    Assert-TeacherPlainPath $Root
    $rootPath = [IO.Path]::GetFullPath($Root).TrimEnd([char[]]@('/','\'))
    foreach ($path in @($DataDir, $Workspace)) {
        $full = [IO.Path]::GetFullPath($path).TrimEnd([char[]]@('/','\'))
        Assert-TeacherPlainPath $full
        if ($full -eq $rootPath -or $full.StartsWith($rootPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or $rootPath.StartsWith($full + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Code, PC data, and work files must not overlap. Choose paths outside the plugin folder.'
        }
    }
}

function Install-TeacherPython([string]$Root, [string]$DataDir, [switch]$AllowPythonInstall) {
    if (-not $AllowPythonInstall) {
        throw 'PYTHON_INSTALL_CONSENT_REQUIRED: No Python 3.12 found. Ask once to download Astral uv and its CPython build into the teacher_doc PC data folder. After approval rerun with -AllowPythonInstall. No download or settings change was made.'
    }
    $architecture = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
    $arch = switch ($architecture) { 'AMD64' { 'x86_64' } 'ARM64' { 'aarch64' } default { throw 'Automatic Python setup supports 64-bit Windows x64/ARM64 only.' } }
    $platform = "$arch-pc-windows-msvc"
    $line = @(Get-Content -LiteralPath (Join-Path $Root 'distribution/runtime-downloads.tsv') | Where-Object { $_.StartsWith($platform + "`t") })
    if ($line.Count -ne 1) { throw 'Missing or ambiguous pinned uv release metadata.' }
    $fields = $line[0].Split("`t")
    $url = $fields[1]; $expected = $fields[2]
    if ($url -notmatch '^https://github\.com/astral-sh/uv/releases/download/0\.12\.22/uv-[a-z0-9_-]+\.zip$' -or $expected -notmatch '^[a-f0-9]{64}$') { throw 'Invalid official uv release metadata.' }
    $managed = Join-Path $DataDir 'managed-python'
    Assert-TeacherPlainPath $managed
    Assert-TeacherPlainPath (Join-Path $managed 'python')
    Assert-TeacherPlainPath (Join-Path $managed 'cache')
    Assert-TeacherPlainPath (Join-Path $managed "python/cpython-3.12.15-windows-$arch-none")
    $owner = Join-Path $managed '.teacher-doc-owner'
    if (Test-Path -LiteralPath $managed) {
        if (-not (Test-Path -LiteralPath $owner) -or (Get-Content -LiteralPath $owner -Raw).Trim() -ne 'teacher-doc-python-v1') { throw 'Existing unmanaged folder preserved: managed-python. Choose a separate -DataDir.' }
    } else {
        New-Item -ItemType Directory -Path $managed -ErrorAction Stop | Out-Null
        [IO.File]::WriteAllText($owner, 'teacher-doc-python-v1')
    }
    $stage = Join-Path $managed ('download-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage | Out-Null
    $savedUv = @{}
    try {
        [Console]::Error.WriteLine('Downloading verified Astral uv 0.12.22: ' + $url)
        $archive = Join-Path $stage 'uv.zip'
        Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing -TimeoutSec 180
        $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) { throw "UV_HASH_MISMATCH: expected $expected; got $actual. Download was not executed." }
        [Console]::Error.WriteLine('uv SHA-256 verified: ' + $actual)
        Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $stage 'unpacked')
        $executables = @(Get-ChildItem -LiteralPath (Join-Path $stage 'unpacked') -Filter uv.exe -Recurse -File)
        if ($executables.Count -ne 1) { throw 'Unexpected uv archive layout.' }
        $uv = $executables[0].FullName
        # Do not inherit mirrors, insecure-host, custom metadata or global uv settings.
        Get-ChildItem Env: | Where-Object { $_.Name -like 'UV_*' } | ForEach-Object { $savedUv[$_.Name] = $_.Value; Remove-Item -LiteralPath ('Env:' + $_.Name) }
        $installDir = Join-Path $managed 'python'
        $metadata = Join-Path $Root 'distribution/python-downloads.json'
        $table = Get-Content -LiteralPath $metadata -Raw -Encoding UTF8 | ConvertFrom-Json
        $key = "cpython-3.12.15-windows-$arch-none"
        $entry = $table.$key
        if (-not $entry -or $entry.url -notmatch '^https://github\.com/astral-sh/python-build-standalone/releases/download/20261001/' -or $entry.sha256 -notmatch '^[a-f0-9]{64}$') { throw 'Invalid pinned CPython download metadata.' }
        [Console]::Error.WriteLine('CPython 3.12.15, SHA-256 enforced by uv: ' + $entry.sha256)
        $uvArgs = @('python', 'install', $key, '--install-dir', $installDir, '--no-bin', '--no-registry', '--no-config', '--managed-python', '--cache-dir', (Join-Path $managed 'cache'), '--python-downloads-json-url', ([Uri]::new($metadata).AbsoluteUri))
        # Capture native stderr as text, not PowerShell 5.1 NativeCommandError.
        # Windows filenames cannot contain double quotes; quote every argument.
        $quotedArgs = ($uvArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
        $uvOut = Join-Path $stage 'uv.stdout'; $uvErr = Join-Path $stage 'uv.stderr'
        $process = Start-Process -FilePath $uv -ArgumentList $quotedArgs -Wait -PassThru -NoNewWindow -RedirectStandardOutput $uvOut -RedirectStandardError $uvErr
        foreach ($log in @($uvOut, $uvErr)) {
            if (Test-Path -LiteralPath $log) { [Console]::Error.WriteLine([IO.File]::ReadAllText($log)) }
        }
        if ($process.ExitCode -ne 0) { throw 'PYTHON_DOWNLOAD_FAILED: uv could not verify/install CPython. Preserve data and retry the same command after fixing the network or permissions.' }
        $python = Join-Path (Join-Path $installDir $key) 'python.exe'
        if (-not (Test-TeacherPython312 $python)) { throw 'Managed Python failed its version/executable check.' }
        $receipt = @{ owner = 'teacher-doc-python-v1'; uv_version = '0.12.22'; uv_sha256 = $actual; python_key = $key; python_sha256 = $entry.sha256; python_url = $entry.url; python = $python; registry_changed = $false; path_changed = $false }
        $receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $managed 'install-receipt.json') -Encoding UTF8
        return $python
    } finally {
        foreach ($name in $savedUv.Keys) { Set-Item -LiteralPath ('Env:' + $name) -Value $savedUv[$name] }
        # Only this invocation's fresh staging directory, never a user folder.
        if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
    }
}
