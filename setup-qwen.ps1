$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.cache\uv'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Install uv first.' }
if (-not (Test-Path '.venv-qwen\Scripts\python.exe')) {
    if (-not (Test-Path '.python\cpython-3.11-windows-x86_64-none\python.exe')) { throw 'Run setup.ps1 first.' }
    uv venv --python .python\cpython-3.11-windows-x86_64-none\python.exe .venv-qwen
    if ($LASTEXITCODE -ne 0) { throw 'Qwen environment creation failed.' }
}
uv pip sync --python .venv-qwen\Scripts\python.exe requirements-qwen-lock.txt --extra-index-url https://download.pytorch.org/whl/cu124 --index-strategy unsafe-best-match
if ($LASTEXITCODE -ne 0) { throw 'Qwen dependency installation failed.' }
uv pip check --python .venv-qwen\Scripts\python.exe
if ($LASTEXITCODE -ne 0) { throw 'Qwen dependency validation failed.' }
& .venv-qwen\Scripts\python.exe -m scripts.download_qwen
if ($LASTEXITCODE -ne 0) { throw 'Qwen download failed. Rerun to resume.' }
& .venv-qwen\Scripts\python.exe -m scripts.download_rubberband
if ($LASTEXITCODE -ne 0) { throw 'Rubber Band download failed. Rerun setup.' }
Write-Host 'Qwen and Rubber Band are installed. Launch the app and select Qwen3-TTS 1.7B Base.'
