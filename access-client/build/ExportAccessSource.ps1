[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Database,
    [Parameter(Mandatory)][string]$Output,
    [string]$SourceRoot,
    # Typed as [string], not [switch] or [bool]: powershell.exe -File passes every
    # argument as a string, so the Python COM bridge's "-Check True" cannot bind to
    # a switch (it spills into the next positional parameter) or to a bool (which
    # rejects the literal string "True").
    [string]$Check = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AccessBuild.Common.psm1') -Force
if (-not $SourceRoot) { $SourceRoot = Join-Path (Split-Path -Parent $PSScriptRoot) 'src' }
$checkRequested = $Check -in @('True', 'true', '1')
Export-AccessSource -Database $Database -Output $Output -SourceRoot $SourceRoot -Check:$checkRequested