[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Database,
    [Parameter(Mandatory)][string]$Source,
    [Parameter(Mandatory)][ValidateSet('x86', 'x64')][string]$Platform
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'AccessBuild.Common.psm1') -Force

$manifest = Get-AccessManifest -SourceRoot $Source
$project = Get-Content -LiteralPath (Join-Path $Source 'project.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$schema = Get-Content -LiteralPath (Join-Path $Source 'tables\schema.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (@($schema.tables).Count -ne 0) { throw 'schema.json must declare zero application tables.' }

$vendor = Join-Path (Split-Path -Parent $Source) 'vendor\json'
$expected = @{
    'JsonConverter.bas' = '1c240aa3c7ef536c25bf44061b02b0fadeb39bfb449f67c419822650e23f6169'
    'LICENSE.txt'       = 'f902104a3e36daea3a33f7adfcd25c5ac69791e9164b83a81b8d0b235728c9bd'
}
foreach ($name in $expected.Keys) {
    $actual = Get-Sha256 -Path (Join-Path $vendor $name)
    if ($actual -ne $expected[$name]) { throw "Vendor hash mismatch for $name." }
}

$app = New-AccessApplication
try {
    Assert-AccessBitness -Application $app -ExpectedPlatform $Platform
    $app.OpenCurrentDatabase((Resolve-Path -LiteralPath $Database).Path)
    Assert-NoUnmanagedObjects -Application $app -Manifest $manifest
    foreach ($ref in $app.VBE.ActiveVBProject.References) {
        if ($project.forbidden_references -contains $ref.Description) {
            throw "Forbidden reference present: $($ref.Description)."
        }
    }
    $app.RunCommand(126) | Out-Null
} finally {
    Close-AccessApplication -Application $app
}
Write-Output "ValidateAccessBuild OK for $Platform"