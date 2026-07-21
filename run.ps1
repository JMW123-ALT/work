$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backendDir = Join-Path $root "backend"
$runtimeDir = Join-Path $root ".runtime"
$backendVenv = Join-Path $backendDir ".venv"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Import-DotEnv {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [bool]$Overwrite = $false
  )

  if (-not (Test-Path -LiteralPath $Path)) {
    return
  }

  Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
      return
    }

    $parts = $line.Split("=", 2)
    $name = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"').Trim("'")
    if ($Overwrite -or -not [Environment]::GetEnvironmentVariable($name, "Process")) {
      [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
  }
}

function Get-PythonVersion {
  param([Parameter(Mandatory = $true)][string]$PythonExe)

  if (-not (Test-Path -LiteralPath $PythonExe)) {
    return $null
  }

  try {
    $version = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
    if ($LASTEXITCODE -eq 0) {
      return ($version | Select-Object -First 1).Trim()
    }
  }
  catch {
    return $null
  }

  return $null
}

function Find-Python312 {
  $candidates = @()

  if ($env:PYTHON312) {
    $candidates += $env:PYTHON312
  }

  if ($env:LOCALAPPDATA) {
    $candidates += (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")
  }
  if ($env:ProgramFiles) {
    $candidates += (Join-Path $env:ProgramFiles "Python312\python.exe")
  }
  if (${env:ProgramFiles(x86)}) {
    $candidates += (Join-Path ${env:ProgramFiles(x86)} "Python312\python.exe")
  }
  if ($env:USERPROFILE) {
    $candidates += (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
  }

  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCommand) {
    $candidates += $pythonCommand.Source
  }

  foreach ($candidate in ($candidates | Select-Object -Unique)) {
    $version = Get-PythonVersion -PythonExe $candidate
    if ($version -like "3.12.*") {
      return $candidate
    }
  }

  throw "Python 3.12 was not found. Install Python 3.12 or set PYTHON312 to python.exe."
}

function New-ProjectVenv {
  param([Parameter(Mandatory = $true)][string]$VenvPath)

  $pythonExe = Join-Path $VenvPath "Scripts\python.exe"
  $version = Get-PythonVersion -PythonExe $pythonExe
  if ($version -like "3.12.*") {
    return
  }

  if (Test-Path -LiteralPath $VenvPath) {
    $resolvedRoot = (Resolve-Path -LiteralPath $root).Path
    $venvFullPath = [System.IO.Path]::GetFullPath($VenvPath)
    if (-not $venvFullPath.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
      throw "Refusing to move venv outside project root: $venvFullPath"
    }

    $backupPath = Join-Path $backendDir (".venv-backup-" + (Get-Date -Format "yyyyMMddHHmmss"))
    Write-Host "Backend virtual environment is not Python 3.12; moving it to $backupPath"
    Move-Item -LiteralPath $VenvPath -Destination $backupPath
  }

  $python312 = Find-Python312
  Write-Host "Creating backend virtual environment with Python 3.12: $python312"
  & $python312 -m venv $VenvPath

  $createdVersion = Get-PythonVersion -PythonExe $pythonExe
  if ($createdVersion -notlike "3.12.*") {
    throw "Created backend virtual environment is not Python 3.12: $createdVersion"
  }
}

function Install-Requirements {
  param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string]$RequirementsPath
  )

  & $PythonExe -m pip install -r $RequirementsPath
}

Import-DotEnv -Path (Join-Path (Split-Path $root -Parent) ".env") -Overwrite:$false
Import-DotEnv -Path (Join-Path $root ".env") -Overwrite:$true

if ($env:EMBEDDING_DASHSCOPE_URL -and $env:EMBEDDING_MODEL -like "*vl*") {
  $env:EMBEDDING_BASE_URL = $env:EMBEDDING_DASHSCOPE_URL
}

New-ProjectVenv -VenvPath $backendVenv

$backendPython = Join-Path $backendVenv "Scripts\python.exe"
Install-Requirements -PythonExe $backendPython -RequirementsPath (Join-Path $backendDir "requirements.txt")

$appPort = if ($env:APP_PORT) { $env:APP_PORT } else { "8000" }

Write-Host "Backend API: http://127.0.0.1:$appPort/api/docs"
Write-Host "Agent chat:  http://127.0.0.1:$appPort/api/chat"
Write-Host "Press Ctrl+C to stop the service."

try {
  Push-Location -LiteralPath $backendDir
  & $backendPython -m uvicorn app.main:app --host 127.0.0.1 --port $appPort
}
finally {
  Pop-Location
}
