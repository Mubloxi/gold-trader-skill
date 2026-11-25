$ErrorActionPreference = 'Stop'
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) { $PSNativeCommandUseErrorActionPreference = $false }
Set-Location $PSScriptRoot
Write-Host 'GOLD SKILL SETUP'
Write-Host '1 Codex + MT5 | 2 Claude Code + MT5 | 3 Codex (attach a chart image) | 4 Claude Code (attach a chart image) | 5 ChatGPT desktop + MT5 | 6 Claude Desktop + MT5'
$choice = Read-Host 'Choose 1 to 6'
if ($choice -notin @('1','2','3','4','5','6')) { Write-Host 'Invalid choice.'; exit 1 }
$platform = if ($choice -in @('1','3','5')) { 'codex' } else { 'claude' }
$folders = if ($platform -eq 'codex') { @('.agents','.codex') } else { @('.claude') }
foreach ($folder in $folders) {
    if (Test-Path (Join-Path $PSScriptRoot $folder)) { Write-Host "Existing $folder found. It will not be overwritten." }
}
foreach ($folder in $folders) { if (-not (Test-Path (Join-Path $PSScriptRoot $folder))) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot "platforms\$platform\$folder") -Destination $PSScriptRoot -Recurse } }
Write-Host 'Skills copied into this project folder.'
if ($choice -in @('1','2','5','6')) {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { Write-Host 'Python 3.11+ is needed for MT5. Install it from https://www.python.org/downloads/windows/, then extract a fresh copy and run setup again.'; exit 1 }
    & py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
    if ($LASTEXITCODE -ne 0) { Write-Host 'Python 3.11 or newer is required.'; exit 1 }
    & py -3 -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('MetaTrader5') else 1)"
    if ($LASTEXITCODE -ne 0) {
        if ((Read-Host 'Install the MetaTrader5 Python package? (y/n)') -ne 'y') { Write-Host 'Setup stopped.'; exit 1 }
        & py -3 -m pip install MetaTrader5
        if ($LASTEXITCODE -ne 0) { Write-Host 'Package installation failed.'; exit 1 }
    }
    Write-Host 'DEMO ACCOUNT: open your broker desktop MT5.'
    Write-Host 'If you have a demo account, select it in MT5 and sign in there. If not, open one with your broker in MT5 first.'
    Write-Host 'If you have one account and it is already signed in, it is selected automatically.'
    Write-Host 'If you have multiple accounts, use the MT5 Navigator account list to select the demo account.'
    Write-Host 'The tool checks that the connected account is a demo and does not store account numbers or passwords.'
    Read-Host 'Press Enter when the demo account is signed in and your gold chart is open' | Out-Null
    Write-Host '1 Pepperstone | 2 Vanga | 3 Other MT5 broker'
    $b = Read-Host 'Choose a broker'
    $broker = switch ($b) { '1' {'pepperstone'} '2' {'vanga'} '3' {'generic'} default {''} }
    if (-not $broker) { Write-Host 'Invalid broker choice.'; exit 1 }
    $symbol = Read-Host 'Gold symbol in Market Watch (Enter for XAUUSD)'
    if (-not $symbol) { $symbol = 'XAUUSD' }
    Write-Host 'Searching common locations for any MT5 terminal. Custom locations may not appear.'
    & py -3 -m gold_desk broker paths generic
    & py -3 -m gold_desk broker setup $broker --symbol $symbol
    if ($LASTEXITCODE -ne 0) {
        $terminal = Read-Host 'Enter the full path to your broker terminal64.exe'
        if (-not $terminal) { Write-Host 'No path supplied.'; exit 1 }
        $terminal = $terminal.Trim().Trim('"')
        & py -3 -m gold_desk broker setup $broker --symbol $symbol --terminal $terminal
        if ($LASTEXITCODE -ne 0) { Write-Host 'Broker setup failed. Check the path.'; exit 1 }
    }
    & py -3 -m gold_desk market --require-demo --require-fresh --log '.\research-run\observations.jsonl' --out '.\research-run\mt5-market.json'
    if ($LASTEXITCODE -ne 0) { Write-Host 'Data check failed. Check MT5 connection, symbol, and market hours.'; exit 1 }
    Write-Host 'Data exported to research-run\mt5-market.json. Compare the candle time and OHLC to MT5.'
}
Write-Host "Open this folder in $platform : $PSScriptRoot"
if ($platform -eq 'codex') {
    if ($choice -in @('1','5')) { Write-Host 'Ask: Use $gold-scanner to review research-run/mt5-market.json. Flag stale data; do not use fixtures.' }
    else { Write-Host 'Attach a chart and ask: Use $gold-scanner to review this chart. Say which values are unclear.' }
} else {
    if ($choice -in @('2','6')) { Write-Host '/gold-scanner Review research-run/mt5-market.json. Flag stale data; do not use fixtures.' }
    else { Write-Host '/gold-scanner Review my attached gold chart and say which values are unclear.' }
}
Write-Host 'No orders are placed. Broker data may be delayed.'

Write-Host 'For desktop apps: open ChatGPT/Codex on this computer and open this project folder. In Claude Desktop, use the exported JSON as an attachment. Desktop skill discovery depends on the app and permissions.'
$prompt = if ($choice -in @('1','5')) { 'Use $gold-scanner to review research-run/mt5-market.json. Explain price timestamps and missing data. Do not use synthetic fixtures.' } elseif ($choice -in @('2','6')) { '/gold-scanner Review research-run/mt5-market.json. Explain price timestamps and missing data. Do not use synthetic fixtures.' } elseif ($platform -eq 'codex') { 'Use $gold-scanner to review my attached gold chart. Say which values are unclear.' } else { '/gold-scanner Review my attached gold chart. Say which values are unclear.' }
try { Set-Clipboard -Value $prompt; Write-Host 'Your prompt was copied to the clipboard. Paste it into your AI app.' } catch { Write-Host $prompt }
