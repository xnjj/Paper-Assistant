$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$entryFile = Join-Path $rootDir "upload_api.py"
$distDir = Join-Path $rootDir "dist-backend"
$workDir = Join-Path $rootDir "build\pyinstaller"
$specDir = $workDir

function Resolve-PythonExecutable {
  if ($env:VIRTUAL_ENV) {
    $venvPython = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
    if (Test-Path $venvPython) {
      return $venvPython
    }
  }

  if ($env:CONDA_PREFIX) {
    $condaPython = Join-Path $env:CONDA_PREFIX "python.exe"
    if (Test-Path $condaPython) {
      return $condaPython
    }
  }

  $pythonCommand = Get-Command python -ErrorAction Stop
  return $pythonCommand.Source
}

if (-not (Test-Path $entryFile)) {
  throw "Backend entry file not found: $entryFile"
}

$pythonExe = Resolve-PythonExecutable
if (-not (Test-Path $pythonExe)) {
  throw "Python executable not found: $pythonExe"
}

Write-Host "Building packaged backend..." -ForegroundColor Cyan
Write-Host "Python: $pythonExe"
Write-Host "Entry: $entryFile"
Write-Host "Output: $distDir"

$arguments = @(
  "-m", "PyInstaller",
  "--noconfirm",
  "--clean",
  "--onedir",
  "--name", "backend",
  "--distpath", $distDir,
  "--workpath", $workDir,
  "--specpath", $specDir,
  "--collect-submodules", "chromadb",
  "--collect-data", "chromadb",
  "--hidden-import", "uvicorn.logging",
  "--hidden-import", "uvicorn.loops.auto",
  "--hidden-import", "uvicorn.protocols.http.auto",
  "--hidden-import", "uvicorn.protocols.websockets.auto",
  "--hidden-import", "uvicorn.lifespan.on",
  "--exclude-module", "matplotlib",
  "--exclude-module", "matplotlib_inline",
  "--exclude-module", "black",
  $entryFile
)

& $pythonExe @arguments

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller build failed."
}

$backendExe = Join-Path $distDir "backend\backend.exe"
if (-not (Test-Path $backendExe)) {
  throw "Packaged backend executable was not generated: $backendExe"
}

Write-Host "Packaged backend created: $backendExe" -ForegroundColor Green
