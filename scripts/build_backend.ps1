$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$entryFile = Join-Path $rootDir "upload_api.py"
$distDir = Join-Path $rootDir "dist-backend"
$workDir = Join-Path $rootDir "build\pyinstaller"
$specDir = $workDir

if (-not (Test-Path $entryFile)) {
  throw "Backend entry file not found: $entryFile"
}

Write-Host "Building packaged backend..." -ForegroundColor Cyan
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
  $entryFile
)

& python @arguments

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller build failed."
}

$backendExe = Join-Path $distDir "backend\backend.exe"
if (-not (Test-Path $backendExe)) {
  throw "Packaged backend executable was not generated: $backendExe"
}

Write-Host "Packaged backend created: $backendExe" -ForegroundColor Green
