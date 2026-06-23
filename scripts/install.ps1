<#
.SYNOPSIS
    Codex Red Team Opt-In Mode — Windows PowerShell installer launcher.
.DESCRIPTION
    Forwards all arguments to install.py. Supports --codex-home, --agents-home,
    --dry-run, and --uninstall.
.EXAMPLE
    .\install.ps1
    .\install.ps1 --codex-home "$env:USERPROFILE\.codex"
    .\install.ps1 --dry-run
    .\install.ps1 --uninstall
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PassedArgs
)

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallPy = Join-Path $ScriptRoot "install.py"

& python $InstallPy @PassedArgs
exit $LASTEXITCODE
