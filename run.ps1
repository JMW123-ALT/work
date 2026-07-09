$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backendDir = Join-Path $root "backend"
$agentDir = Join-Path $root "agent"
$runtimeDir = Join-Path $root ".runtime"
$backendVenv = Join-Path $backendDir ".venv"
$agentVenv = Join-Path $agentDir ".venv"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Import-DotEnv {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [bool]$Overwrite = $false
  )

  if (-not (Test-Path $Path)) {
    return
  }

  Get-Content -Encoding UTF8 $Path | ForEach-Object {
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

Import-DotEnv -Path (Join-Path (Split-Path $root -Parent) ".env") -Overwrite:$false
Import-DotEnv -Path (Join-Path $root ".env") -Overwrite:$true

if ($env:EMBEDDING_DASHSCOPE_URL -and $env:EMBEDDING_MODEL -like "*vl*") {
  $env:EMBEDDING_BASE_URL = $env:EMBEDDING_DASHSCOPE_URL
}

function New-ProjectVenv {
  param(
    [Parameter(Mandatory = $true)][string]$VenvPath
  )

  $pythonExe = Join-Path $VenvPath "Scripts\python.exe"
  if (Test-Path $pythonExe) {
    return
  }

  if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m venv $VenvPath
    return
  }

  if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv $VenvPath
    return
  }

  throw "Python was not found. Install Python 3 or make sure the py launcher is available."
}

function Install-Requirements {
  param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string]$RequirementsPath
  )

  & $PythonExe -m pip install -r $RequirementsPath
}

New-ProjectVenv -VenvPath $backendVenv
New-ProjectVenv -VenvPath $agentVenv

$backendPython = Join-Path $backendVenv "Scripts\python.exe"
$agentPython = Join-Path $agentVenv "Scripts\python.exe"

Install-Requirements -PythonExe $backendPython -RequirementsPath (Join-Path $backendDir "requirements.txt")
Install-Requirements -PythonExe $agentPython -RequirementsPath (Join-Path $agentDir "requirements.txt")

$backendOutLog = Join-Path $runtimeDir "backend.out.log"
$backendErrLog = Join-Path $runtimeDir "backend.err.log"
$agentOutLog = Join-Path $runtimeDir "agent.out.log"
$agentErrLog = Join-Path $runtimeDir "agent.err.log"

$backendCommand = @"
Set-Location '$backendDir'
& '$backendPython' -m uvicorn app.main:app --host 127.0.0.1 --port 8001
"@

$agentCommand = @"
Set-Location '$agentDir'
`$env:RETRIEVER_PROVIDER = 'shujuku'
`$env:SHUJUKU_SEARCH_URL = 'http://127.0.0.1:8001/api/v1/search'
& '$agentPython' -m uvicorn wc_agent.api:app --host 127.0.0.1 --port 8000
"@

$backendProcess = Start-Process powershell.exe `
  -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand) `
  -RedirectStandardOutput $backendOutLog `
  -RedirectStandardError $backendErrLog `
  -WindowStyle Hidden `
  -PassThru

$agentProcess = Start-Process powershell.exe `
  -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $agentCommand) `
  -RedirectStandardOutput $agentOutLog `
  -RedirectStandardError $agentErrLog `
  -WindowStyle Hidden `
  -PassThru

Write-Host "Backend API: http://127.0.0.1:8001/api/docs"
Write-Host "Agent API:   http://127.0.0.1:8000/docs"
Write-Host "Backend logs: $backendOutLog / $backendErrLog"
Write-Host "Agent logs:   $agentOutLog / $agentErrLog"
Write-Host "Press Ctrl+C to stop both services."

try {
  while (-not $backendProcess.HasExited -and -not $agentProcess.HasExited) {
    Start-Sleep -Seconds 1
  }
}
finally {
  foreach ($process in @($backendProcess, $agentProcess)) {
    if ($process -and -not $process.HasExited) {
      Stop-Process -Id $process.Id -Force
    }
  }
}
