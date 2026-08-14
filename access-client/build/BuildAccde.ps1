[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Database,
    [Parameter(Mandatory)][string]$Output,
    [Parameter(Mandatory)][ValidateSet('x86', 'x64')][string]$Platform,
    [Parameter(Mandatory)][string]$ClientVersion
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AccessBuild.Common.psm1') -Force
Build-AccessAccde -Database $Database -Output $Output -Platform $Platform -ClientVersion $ClientVersion