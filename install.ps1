param(
    [Parameter(Mandatory=$true)][ValidateSet("claude","codex")][string]$Platform,
    [Parameter(Mandatory=$true)][string]$Target
)
$ErrorActionPreference = "Stop"
$Installer = Join-Path $PSScriptRoot "scripts/install.py"
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $Installer $Platform --target $Target
} else {
    & python $Installer $Platform --target $Target
}
exit $LASTEXITCODE
