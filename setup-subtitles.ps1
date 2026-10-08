$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
# Qwen's isolated environment also hosts the offline subtitle worker.
if (-not (Test-Path '.venv-qwen\Scripts\python.exe')) {
    throw 'Run setup-qwen.ps1 first to create the isolated worker environment.'
}
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.cache\uv'
uv pip sync --python .venv-qwen\Scripts\python.exe requirements-qwen-lock.txt --extra-index-url https://download.pytorch.org/whl/cu124 --index-strategy unsafe-best-match
if ($LASTEXITCODE -ne 0) { throw 'Subtitle dependency installation failed.' }
& .venv-qwen\Scripts\python.exe -m scripts.download_subtitles
if ($LASTEXITCODE -ne 0) { throw 'Subtitle model download failed. Rerun to resume.' }
Write-Host 'Subtitles are installed. Open the Audio to subtitles tab.'
