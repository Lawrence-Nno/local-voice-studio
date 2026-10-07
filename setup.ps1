$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PSScriptRoot '.python'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is required. Install uv first, then run this script again.'
}
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    $taskDrive = [System.IO.DriveInfo]::new([System.IO.Path]::GetPathRoot($PSScriptRoot))
    if ($taskDrive.AvailableFreeSpace -lt 15GB) { throw 'Allow at least 15 GB free for initial setup.' }
    uv python install 3.11
    if ($LASTEXITCODE -ne 0) { throw 'Python installation failed.' }
    uv venv --python 3.11 .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
Write-Host 'Installing project-local CUDA runtime and dependencies. Initial downloads are several GB.'
if (Test-Path 'requirements-lock.txt') {
    uv pip sync --python .venv\Scripts\python.exe requirements-lock.txt --extra-index-url https://download.pytorch.org/whl/cu124 --index-strategy unsafe-best-match
} else {
    uv pip install --python .venv\Scripts\python.exe torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
    if ($LASTEXITCODE -ne 0) { throw 'CUDA PyTorch installation failed.' }
    uv pip install --python .venv\Scripts\python.exe chatterbox-tts==0.1.7 setuptools==80.9.0
}
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
uv pip check --python .venv\Scripts\python.exe
if ($LASTEXITCODE -ne 0) { throw 'Dependency validation failed.' }
& .venv\Scripts\python.exe -m scripts.download_model
if ($LASTEXITCODE -ne 0) { throw 'Model download failed. Rerun setup to resume.' }
& .venv\Scripts\python.exe -m scripts.diagnose
if ($LASTEXITCODE -ne 0) { throw 'Runtime validation failed.' }
Write-Host 'Setup complete. Double-click launch.cmd to open Local Voice Studio.'
