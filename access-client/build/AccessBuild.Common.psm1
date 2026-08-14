#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Access object-type constants used by SaveAsText / LoadFromText.
$script:AcForm = 2
$script:AcReport = 3
$script:AcMacro = 4
$script:AcModule = 5
$script:AcQuitSaveNone = 2

# VBIDE component types. Referenced late-bound only; the production project
# never gains a VBIDE reference.
$script:VbextStdModule = 1
$script:VbextClassModule = 2

function New-AccessApplication {
    [CmdletBinding()]
    param()
    $app = New-Object -ComObject Access.Application
    $app.Visible = $false
    return $app
}

function Close-AccessApplication {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Application)
    # DEVIATION from the plan snippet, deliberate and load-bearing:
    # Application.CloseCurrentDatabase() raises a modal "Save As" dialog against a
    # database created in the same automation session, and headless Access then
    # blocks forever. Quit(1 = acQuitSaveAll) releases the database and exits
    # without prompting, which is what the snippet intended. acQuitSaveNone (2) is
    # NOT usable here: it discards the imported VBA modules, leaving a database
    # whose VBComponents lookup fails with "Subscript out of range".
    try {
        foreach ($form in $Application.CurrentProject.AllForms) {
            if ($form.IsLoaded) {
                try { $Application.DoCmd.Close(2, $form.Name, 2) } catch { }
            }
        }
    } catch { }
    try {
        $Application.Quit(1)
    } catch {
        if ($_.Exception.Message -notmatch 'database is not open|closed or doesn''t exist|no current database') {
            throw
        }
    } finally {
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($Application) } catch { }
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}
function Assert-AccessBitness {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Application,
        [Parameter(Mandatory)][ValidateSet('x86', 'x64')][string]$ExpectedPlatform
    )
    $processPlatform = if ([Environment]::Is64BitProcess) { 'x64' } else { 'x86' }
    if ($processPlatform -ne $ExpectedPlatform) {
        throw "PowerShell platform $processPlatform does not match requested Access platform $ExpectedPlatform."
    }
    $configuredPlatform = (Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration' -ErrorAction Stop).Platform
    if ($configuredPlatform -ne $ExpectedPlatform) {
        throw "Installed Access platform $configuredPlatform does not match requested platform $ExpectedPlatform."
    }
    [void]$Application.hWndAccessApp
}

function Get-AccessManifest {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$SourceRoot)
    $path = Join-Path $SourceRoot 'manifest.json'
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Manifest not found at $path."
    }
    return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function ConvertTo-CanonicalText {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$ObjectType
    )
    # Normalize to CRLF, strip trailing whitespace per line, and end with exactly
    # one terminator. Written without a shrink-the-array loop: PowerShell collapses
    # a one-element array to a scalar, after which index -1 addresses a character
    # and the slice throws IndexOutOfRangeException.
    $text = [IO.File]::ReadAllText($Path)
    $text = $text -replace "`r`n", "`n" -replace "`r", "`n"
    $lines = @($text -split "`n" | ForEach-Object { $_.TrimEnd() })
    if ($ObjectType -eq 'form') {
        # Access regenerates this form-specific checksum on import, and can
        # duplicate this adjacent property. Neither represents source intent.
        $lines = @($lines | Where-Object { $_ -notmatch '^\s*Checksum =-?\d+$' })
        $deduplicated = New-Object 'System.Collections.Generic.List[string]'
        $previousWasNoSaveCti = $false
        $insideNameMap = $false
        foreach ($line in $lines) {
            if ($line -eq '    NameMap = Begin') {
                $insideNameMap = $true
                continue
            }
            if ($insideNameMap) {
                if ($line -eq '    End') { $insideNameMap = $false }
                continue
            }
            $isNoSaveCti = $line -eq '    NoSaveCTIWhenDisabled =1'
            if ($isNoSaveCti -and $previousWasNoSaveCti) { continue }
            $deduplicated.Add($line)
            $previousWasNoSaveCti = $isNoSaveCti
        }
        $lines = @($deduplicated)
    }
    $joined = ($lines -join "`n").TrimEnd("`n")
    $canonical = ($joined -replace "`n", "`r`n") + "`r`n"
    [IO.File]::WriteAllText($Path, $canonical, (New-Object Text.UTF8Encoding($false)))
    return $canonical
}

function ConvertTo-AccessJsonImportSource {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$SourceFile)
    # VBA-JSON v2.3.1 declares a compile-time Dictionary type. Access reserves
    # that class name, so importing it directly requires the forbidden Scripting
    # Runtime reference. Transform exactly those two lines into late-bound Object
    # use for the transient import copy; never mutate the hash-pinned vendor file.
    $source = [IO.File]::ReadAllText($SourceFile)
    $typedDeclaration = 'Private Function json_ParseObject(json_String As String, ByRef json_Index As Long) As Dictionary'
    $objectDeclaration = 'Private Function json_ParseObject(json_String As String, ByRef json_Index As Long) As Object'
    $typedConstruction = 'Set json_ParseObject = New Dictionary'
    $lateBoundConstruction = 'Set json_ParseObject = CreateObject("Scripting.Dictionary")'
    if (
        ([regex]::Matches($source, [regex]::Escape($typedDeclaration))).Count -ne 1 -or
        ([regex]::Matches($source, [regex]::Escape($typedConstruction))).Count -ne 1
    ) {
        throw 'Vendor JsonConverter source did not match the expected v2.3.1 import shape.'
    }
    $adapted = $source.Replace($typedDeclaration, $objectDeclaration).Replace($typedConstruction, $lateBoundConstruction)
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ("JsonConverter.Access.$([guid]::NewGuid().ToString('N')).bas")
    [IO.File]::WriteAllText($temporary, $adapted, (New-Object Text.UTF8Encoding($false)))
    return $temporary
}

function Get-Sha256 {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Path).Path)
        return (-join ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }))
    } finally {
        $sha.Dispose()
    }
}

function Get-AccessObjectTypeCode {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Type)
    switch ($Type) {
        'form'   { return $script:AcForm }
        'report' { return $script:AcReport }
        'macro'  { return $script:AcMacro }
        default  { throw "Unsupported SaveAsText object type '$Type'." }
    }
}

function Assert-NoUnmanagedObjects {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Application, [Parameter(Mandatory)]$Manifest)
    $named = @($Manifest.objects | ForEach-Object { $_.name })
    $db = $Application.CurrentDb()
    foreach ($table in $db.TableDefs) {
        if ($table.Name -notlike 'MSys*' -and $table.Name -notlike '~*') {
            throw "Local application table '$($table.Name)' is forbidden by AC-01."
        }
    }
    foreach ($query in $db.QueryDefs) {
        if ($query.Name -notlike '~*') {
            throw "Stored query '$($query.Name)' is forbidden by AC-01."
        }
    }
    foreach ($report in $Application.CurrentProject.AllReports) {
        throw "Report '$($report.Name)' is forbidden by AC-01."
    }
    foreach ($form in $Application.CurrentProject.AllForms) {
        if ($named -notcontains $form.Name) {
            throw "Form '$($form.Name)' is not present in manifest.json."
        }
    }
    foreach ($macro in $Application.CurrentProject.AllMacros) {
        if ($named -notcontains $macro.Name) {
            throw "Macro '$($macro.Name)' is not present in manifest.json."
        }
    }
    foreach ($component in $Application.VBE.ActiveVBProject.VBComponents) {
        if ($component.Type -in @($script:VbextStdModule, $script:VbextClassModule)) {
            if ($named -notcontains $component.Name) {
                throw "Module '$($component.Name)' is not present in manifest.json."
            }
        }
    }
}

function Export-AccessSource {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Database,
        [Parameter(Mandatory)][string]$Output,
        [Parameter(Mandatory)][string]$SourceRoot,
        [switch]$Check
    )
    $manifest = Get-AccessManifest -SourceRoot $SourceRoot
    if (-not (Test-Path -LiteralPath $Output)) {
        New-Item -ItemType Directory -Force -Path $Output | Out-Null
    }
    # `Import-AccessSource` consumes this metadata in addition to manifested
    # Access objects. Keep an export self-contained so it can be used as the
    # next source root rather than merely as a manifest comparison artifact.
    foreach ($relativePath in @('project.json', 'tables/schema.json', 'reports/.gitkeep', 'queries/.gitkeep')) {
        $sourcePath = Join-Path $SourceRoot $relativePath
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            throw "Required source metadata is missing: $sourcePath."
        }
        $targetPath = Join-Path $Output $relativePath
        $targetDirectory = Split-Path -Parent $targetPath
        if (-not (Test-Path -LiteralPath $targetDirectory)) {
            New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
        }
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
    }
    $app = New-AccessApplication
    try {
        $app.OpenCurrentDatabase((Resolve-Path -LiteralPath $Database).Path)
        # CurrentDb() is not immediately available after OpenCurrentDatabase; without
        # this settle the DAO database object comes back without TableDefs.
        Start-Sleep -Milliseconds 800
        Assert-NoUnmanagedObjects -Application $app -Manifest $manifest
        $ordered = @($manifest.objects | Sort-Object -Property @{Expression = 'type' }, @{Expression = 'name' })
        foreach ($object in $ordered) {
            $sourceObjectPath = [string]$object.path
            # The checked-in source root legitimately reaches pinned dependencies
            # through ../vendor and ../tests. An export is a new source root, so
            # materialize those files beneath it and rewrite only its manifest.
            $exportObjectPath = $sourceObjectPath -replace '^(\.\.[\\/])+', ''
            if (
                [string]::IsNullOrWhiteSpace($exportObjectPath) -or
                [IO.Path]::IsPathRooted($exportObjectPath) -or
                $exportObjectPath -match '(^|[\\/])\.\.([\\/]|$)'
            ) {
                throw "Export object path must remain inside the output root: $sourceObjectPath."
            }
            $object.path = $exportObjectPath
            $target = Join-Path $Output $exportObjectPath
            $dir = Split-Path -Parent $target
            if (-not (Test-Path -LiteralPath $dir)) {
                New-Item -ItemType Directory -Force -Path $dir | Out-Null
            }
            $isVendor = ($object.PSObject.Properties.Name -contains 'vendor') -and $object.vendor
            if ($isVendor) {
                # Vendor bytes are immutable and hash-pinned. Never re-export them
                # through Access, but copy the pinned source bytes into the exported
                # layout so `Import-AccessSource` can consume that layout directly.
                $pinned = (Resolve-Path -LiteralPath (Join-Path $SourceRoot $sourceObjectPath)).Path
                Copy-Item -LiteralPath $pinned -Destination $target -Force
                $object | Add-Member -NotePropertyName 'sha256' -NotePropertyValue (Get-Sha256 -Path $target) -Force
                continue
            }
            if ($object.type -eq 'module') {
                $component = $app.VBE.ActiveVBProject.VBComponents.Item($object.name)
                $component.Export($target)
            } else {
                $code = Get-AccessObjectTypeCode -Type $object.type
                $app.SaveAsText($code, $object.name, $target)
            }
            [void](ConvertTo-CanonicalText -Path $target -ObjectType $object.type)
            $object | Add-Member -NotePropertyName 'sha256' -NotePropertyValue (Get-Sha256 -Path $target) -Force
        }
    } finally {
        Close-AccessApplication -Application $app
    }
    $manifestPath = Join-Path $Output 'manifest.json'
    # Write UTF-8 without BOM: Set-Content -Encoding UTF8 emits a BOM in Windows
    # PowerShell, which breaks Python's read_text("utf-8") on the manifest.
    [IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 6), (New-Object Text.UTF8Encoding($false)))
    if ($Check -and -not (Test-Path -LiteralPath $manifestPath)) {
        throw "Export did not produce a manifest at $manifestPath."
    }
    return $Output
}

function Set-AccessProjectPolicy {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Application, [Parameter(Mandatory)]$Project)
    $map = @{
        'StartUpForm'           = $Project.startup_form
        'AllowBypassKey'        = [bool]$Project.allow_bypass_key
        'StartUpShowDBWindow'   = [bool]$Project.display_navigation_pane
        'UseMDIMode'            = if ($Project.display_document_tabs) { 0 } else { 1 }
        'AllowSpecialKeys'      = [bool]$Project.use_access_special_keys
    }
    foreach ($name in $map.Keys) {
        $value = $map[$name]
        try {
            $Application.CurrentDb().Properties.Item($name).Value = $value
        } catch {
            $prop = $Application.CurrentDb().CreateProperty($name, 10, [string]$value)
            try { $Application.CurrentDb().Properties.Append($prop) } catch { }
        }
    }
}

function Import-AccessSource {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Database,
        [ValidateSet('Test', 'Release')][string]$Configuration = 'Release'
    )
    $manifest = Get-AccessManifest -SourceRoot $Source
    $projectPath = Join-Path $Source 'project.json'
    $project = Get-Content -LiteralPath $projectPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (Test-Path -LiteralPath $Database) {
        Remove-Item -LiteralPath $Database -Force
    }
    $app = New-AccessApplication
    try {
        $app.NewCurrentDatabase($Database)
        Start-Sleep -Milliseconds 500
        # A new Access database opens with an unsaved Table1; discard it so the
        # zero-application-tables invariant holds and nothing prompts on exit.
        try { $app.DoCmd.Close(0, 'Table1', 2) } catch { }
        $ordered = @($manifest.objects | Sort-Object -Property order)
        foreach ($object in $ordered) {
            $isTestOnly = ($object.PSObject.Properties.Name -contains 'test_only') -and $object.test_only
            if ($isTestOnly -and $Configuration -ne 'Test') { continue }
            $sourceFile = (Resolve-Path -LiteralPath (Join-Path $Source $object.path)).Path
            if ($object.type -eq 'module') {
                $temporaryImportFile = $null
                try {
                    $isVendor = ($object.PSObject.Properties.Name -contains 'vendor') -and $object.vendor
                    if ($isVendor -and $object.name -eq 'JsonConverter') {
                        $temporaryImportFile = ConvertTo-AccessJsonImportSource -SourceFile $sourceFile
                        $sourceFile = $temporaryImportFile
                    }
                    $component = $app.VBE.ActiveVBProject.VBComponents.Import($sourceFile)
                } finally {
                    if ($temporaryImportFile) {
                        Remove-Item -LiteralPath $temporaryImportFile -Force -ErrorAction SilentlyContinue
                    }
                }
                # VBE imports a component into the project but leaves it unsaved.
                # Save it under its imported name before compilation/close so Access
                # cannot raise a headless "Save As" modal during shutdown.
                $app.DoCmd.Save($script:AcModule, $component.Name)
            } else {
                $code = Get-AccessObjectTypeCode -Type $object.type
                $app.LoadFromText($code, $object.name, $sourceFile)
            }
        }
        # VBComponents.Import only stages modules in memory; without an explicit
        # compile-and-save they are silently lost when the database closes.
        $app.RunCommand(126) | Out-Null
        Set-AccessProjectPolicy -Application $app -Project $project
    } finally {
        Close-AccessApplication -Application $app
    }
    return $Database
}
function Build-AccessAccde {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Database,
        [Parameter(Mandatory)][string]$Output,
        [Parameter(Mandatory)][ValidateSet('x86', 'x64')][string]$Platform,
        [Parameter(Mandatory)][string]$ClientVersion,
        [ValidateRange(1, 1800)][int]$InteractiveTimeoutSeconds = 300
    )
    if (Test-Path -LiteralPath $Output) {
        Remove-Item -LiteralPath $Output -Force
    }
    $resolved = (Resolve-Path -LiteralPath $Database).Path
    $app = New-AccessApplication
    try {
        Assert-AccessBitness -Application $app -ExpectedPlatform $Platform
        $app.OpenCurrentDatabase($resolved)
        # Compile and persist every module before the ACCDE operation.
        $app.RunCommand(126) | Out-Null   # acCmdCompileAndSaveAllModules
        # Access explicitly refuses Make ACCDE when it is invoked from a macro or
        # VBA/automation. Keep this as a controlled native UI action: the operator
        # chooses File > Save As > Make ACCDE and saves at the exact requested path.
        $app.Visible = $true
        Write-Host "In Access choose File > Save As > Make ACCDE and save exactly to: $Output"
        $deadline = [DateTime]::UtcNow.AddSeconds($InteractiveTimeoutSeconds)
        while (-not (Test-Path -LiteralPath $Output) -and [DateTime]::UtcNow -lt $deadline) {
            Start-Sleep -Seconds 1
        }
        if (-not (Test-Path -LiteralPath $Output)) {
            throw "Timed out waiting for the native Make ACCDE workflow to create $Output."
        }
    } finally {
        Close-AccessApplication -Application $app
    }
    if (-not (Test-Path -LiteralPath $Output)) {
        throw "ACCDE was not produced at $Output."
    }
    $verify = New-AccessApplication
    try {
        Assert-AccessBitness -Application $verify -ExpectedPlatform $Platform
        $verify.OpenCurrentDatabase($Output, $true)
    } finally {
        Close-AccessApplication -Application $verify
    }
    Write-Output "ACCDE $ClientVersion built for $Platform at $Output"
    return $Output
}

function Test-AccessSourceRoundTrip {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SourceRoot,
        [Parameter(Mandatory)][string]$ExportedRoot
    )
    $expected = Get-AccessManifest -SourceRoot $SourceRoot
    $actual = Get-AccessManifest -SourceRoot $ExportedRoot
    $expectedNames = @($expected.objects | ForEach-Object { $_.name })
    $actualNames = @($actual.objects | ForEach-Object { $_.name })
    if (Compare-Object -ReferenceObject $expectedNames -DifferenceObject $actualNames -SyncWindow 0) {
        throw "Round-trip object set differs between $SourceRoot and $ExportedRoot."
    }
    return $true
}

Export-ModuleMember -Function New-AccessApplication, Close-AccessApplication, Assert-AccessBitness,
    Get-AccessManifest, ConvertTo-CanonicalText, Get-Sha256, Get-AccessObjectTypeCode,
    Assert-NoUnmanagedObjects, Export-AccessSource, Set-AccessProjectPolicy, Import-AccessSource,
    Build-AccessAccde, Test-AccessSourceRoundTrip
