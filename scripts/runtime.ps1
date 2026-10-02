# Shared Windows runtime lookup. Read-only; no downloads or persistent env changes.
function Get-HwpdocWorkspace {
    param([string]$Workspace, [object[]]$CommandArgs = @())
    if (-not $Workspace) {
        for ($i = 0; $i -lt $CommandArgs.Count; $i++) {
            if ($CommandArgs[$i] -eq '--workspace') {
                if ($i + 1 -ge $CommandArgs.Count) { throw '--workspace requires a folder' }
                $Workspace = [string]$CommandArgs[$i + 1]
                break
            }
            if ([string]$CommandArgs[$i] -like '--workspace=*') {
                $Workspace = ([string]$CommandArgs[$i]).Substring(12)
                break
            }
        }
    }
    if (-not $Workspace) { $Workspace = $env:HWPDOC_WORKSPACE }
    if ($Workspace) { return [IO.Path]::GetFullPath($Workspace) }
    $folder = [IO.DirectoryInfo](Get-Location).Path
    while ($null -ne $folder) {
        if (Test-Path -LiteralPath (Join-Path $folder.FullName '.hwpdoc/workspace.json') -PathType Leaf) { return $folder.FullName }
        $folder = $folder.Parent
    }
    return $null
}

function Get-HwpdocData {
    param([string]$Workspace, [string]$DataDir, [object[]]$CommandArgs = @())
    if ($DataDir) { return [IO.Path]::GetFullPath($DataDir) }
    if ($env:HWPDOC_PC_DATA) { return [IO.Path]::GetFullPath($env:HWPDOC_PC_DATA) }
    $workspaceRoot = Get-HwpdocWorkspace -Workspace $Workspace -CommandArgs $CommandArgs
    if ($workspaceRoot) {
        $receiptPath = Join-Path $workspaceRoot '.hwpdoc/onboarding.json'
        if (Test-Path -LiteralPath $receiptPath -PathType Leaf) {
            $receipt = Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($key in @('pc_data', 'python')) {
                if ($receipt.$key -isnot [string] -or -not $receipt.$key.Trim() -or -not [IO.Path]::IsPathRooted($receipt.$key)) {
                    throw "Invalid installation receipt path: $key. Preserve the receipt and check the actual PC paths."
                }
            }
            $configPath = Join-Path $receipt.pc_data 'runtime.json'
            if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
                throw "Recorded runtime.json not found: $configPath. Check moved/copied PC paths; do not reinstall or use a default path."
            }
            $runtime = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($runtime.version -ne 1 -or $runtime.python -cne $receipt.python) {
                throw 'Installation receipt and runtime.json Python paths do not match. Verify the intended PC data folder.'
            }
            if (-not (Test-Path -LiteralPath $receipt.python -PathType Leaf)) { throw 'Recorded Python is missing. Preserve existing files and repair the runtime.' }
            return [IO.Path]::GetFullPath($receipt.pc_data)
        }
    }
    return Join-Path $env:LOCALAPPDATA 'hwpdoc'
}

function Get-HwpdocPython {
    param([string]$Workspace, [object[]]$CommandArgs = @())
    $taskData = Get-HwpdocData -Workspace $Workspace -CommandArgs $CommandArgs
    $taskConfig = Join-Path $taskData 'runtime.json'
    if (Test-Path -LiteralPath $taskConfig) {
        $taskRuntime = Get-Content -LiteralPath $taskConfig -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($taskRuntime.version -ne 1) { throw 'Unsupported hwpdoc runtime config version' }
        $taskPython = $taskRuntime.python
        if ($taskPython -isnot [string] -or -not [IO.Path]::IsPathRooted($taskPython) -or -not (Test-Path -LiteralPath $taskPython -PathType Leaf)) {
            throw 'Configured hwpdoc Python not found; repair runtime.json before continuing'
        }
        return $taskPython
    }
    $workspaceRoot = Get-HwpdocWorkspace -Workspace $Workspace -CommandArgs $CommandArgs
    if ($workspaceRoot -and (Test-Path -LiteralPath (Join-Path $workspaceRoot '.hwpdoc/onboarding.json') -PathType Leaf)) {
        throw "Selected PC data runtime.json not found: $taskConfig. Check the existing installation path."
    }
    # Compatibility for an older PC without an installation receipt.
    $taskPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    if (Test-Path -LiteralPath $taskPython -PathType Leaf) { return $taskPython }
    foreach ($taskKey in @('HKCU:\Software\Python\PythonCore\3.12\InstallPath', 'HKLM:\Software\Python\PythonCore\3.12\InstallPath')) {
        if (Test-Path -LiteralPath $taskKey) {
            $taskPython = (Get-ItemProperty -LiteralPath $taskKey).ExecutablePath
            if ($taskPython -and (Test-Path -LiteralPath $taskPython -PathType Leaf)) { return $taskPython }
        }
    }
    throw 'Python 3.12 not found. Read the setup skill and installation receipt; do not guess another runtime. Protection is unverified.'
}
