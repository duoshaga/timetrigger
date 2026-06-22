$stamp = Get-Date -Format "yyyyMMddHHmmss"
$base = Join-Path $env:TEMP "timetrigger-pyinstaller-$stamp"
$dist = Join-Path $base "dist"
$work = Join-Path $base "build"

New-Item -ItemType Directory -Force -Path $base | Out-Null
python -m PyInstaller --onefile --windowed --name TimeTrigger --workpath $work --distpath $dist --noconfirm main.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

New-Item -ItemType Directory -Force -Path ".\dist_final" | Out-Null
Copy-Item -LiteralPath (Join-Path $dist "TimeTrigger.exe") -Destination ".\dist_final\TimeTrigger.exe" -Force
Copy-Item -LiteralPath ".\reminder_times.txt" -Destination ".\dist_final\reminder_times.txt" -Force
if (Test-Path -LiteralPath ".\reminder_enabled.txt") {
    Copy-Item -LiteralPath ".\reminder_enabled.txt" -Destination ".\dist_final\reminder_enabled.txt" -Force
}
