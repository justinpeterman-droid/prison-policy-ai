[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Source,
    [Parameter(Mandatory)][string]$Database,
    [ValidateSet('Test', 'Release')][string]$Configuration = 'Release'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AccessBuild.Common.psm1') -Force
Import-AccessSource -Source $Source -Database $Database -Configuration $Configuration