[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Database,
    [Parameter(Mandatory)][ValidateSet('x86', 'x64')][string]$Platform
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AccessBuild.Common.psm1') -Force
$app = New-AccessApplication
try {
    Assert-AccessBitness -Application $app -ExpectedPlatform $Platform
    $app.OpenCurrentDatabase((Resolve-Path -LiteralPath $Database).Path)
    $result = $app.Run('Test_RunAll')
    Write-Output $result
} finally {
    Close-AccessApplication -Application $app
}