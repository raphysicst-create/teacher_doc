# Shared Windows bootstrap. No profile edits, package installation or downloads.
function Get-HwpdocPython {
    $taskData = if ($env:HWPDOC_PC_DATA) { $env:HWPDOC_PC_DATA } else { Join-Path $env:LOCALAPPDATA 'hwpdoc' }
    $taskConfig = Join-Path $taskData 'runtime.json'
    if (Test-Path -LiteralPath $taskConfig) {
        $taskRuntime = Get-Content -LiteralPath $taskConfig -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($taskRuntime.version -ne 1) { throw 'Unsupported hwpdoc runtime config version' }
        $taskPython = $taskRuntime.python
        if (-not $taskPython -or -not (Test-Path -LiteralPath $taskPython -PathType Leaf)) {
            throw 'Configured hwpdoc Python not found; repair runtime.json before continuing'
        }
        return $taskPython
    }
    # Python 3.12 is the tested runtime; resolve its installation per user/PC.
    $taskPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    if (Test-Path -LiteralPath $taskPython -PathType Leaf) { return $taskPython }
    foreach ($taskKey in @('HKCU:\Software\Python\PythonCore\3.12\InstallPath', 'HKLM:\Software\Python\PythonCore\3.12\InstallPath')) {
        if (Test-Path -LiteralPath $taskKey) {
            $taskPython = (Get-ItemProperty -LiteralPath $taskKey).ExecutablePath
            if ($taskPython -and (Test-Path -LiteralPath $taskPython -PathType Leaf)) { return $taskPython }
        }
    }
    throw 'Python 3.12 not found. Install Python or configure %LOCALAPPDATA%\hwpdoc\runtime.json. Protection is unverified.'
}
