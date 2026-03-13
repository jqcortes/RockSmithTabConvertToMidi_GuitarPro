param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Path $PSScriptRoot -Parent
$propertiesPath = Join-Path $projectRoot "config\audiveris.properties"

$checks = New-Object System.Collections.Generic.List[object]

function Add-Check {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail
    )

    $checks.Add([pscustomobject]@{
        Name = $Name
        Ok = $Ok
        Detail = $Detail
    })
}

function Get-CommandPath {
    param([string]$CommandName)

    $command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        return $null
    }
    return $command.Source
}

function Read-PropertiesValue {
    param(
        [string]$Path,
        [string]$Key
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    foreach ($line in Get-Content -Path $Path -Encoding UTF8) {
        if ($line -match '^\s*#') {
            continue
        }
        if ($line -match ('^\s*' + [regex]::Escape($Key) + '\s*=\s*(.+?)\s*$')) {
            return $Matches[1]
        }
    }

    return $null
}

function Normalize-PathValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }

    $normalized = $Value.Trim()

    # Accept common INI styles: "C:\path\to\file" or 'C:\path\to\file'
    if (($normalized.StartsWith('"') -and $normalized.EndsWith('"')) -or
        ($normalized.StartsWith("'") -and $normalized.EndsWith("'"))) {
        $normalized = $normalized.Substring(1, $normalized.Length - 2)
    }

    return $normalized.Trim()
}

$javaPath = Get-CommandPath "java"
if ($null -ne $javaPath) {
    # In PowerShell 7, native stderr can become a terminating error depending on preferences.
    # Execute via cmd so we can safely capture java -version output as plain text.
    $javaVersion = (cmd /c "`"$javaPath`" -version 2>&1" | Select-Object -First 1).Trim()
    Add-Check -Name "Java" -Ok $true -Detail "$javaVersion [$javaPath]"
} else {
    Add-Check -Name "Java" -Ok $false -Detail "java was not found on PATH. Install Java 17+ and add it to PATH."
}

$pdfInfoPath = Get-CommandPath "pdfinfo"
if ($null -ne $pdfInfoPath) {
    Add-Check -Name "Poppler pdfinfo" -Ok $true -Detail $pdfInfoPath
} else {
    Add-Check -Name "Poppler pdfinfo" -Ok $false -Detail "pdfinfo was not found on PATH. Install Poppler and add it to PATH."
}

$pdfToPpmPath = Get-CommandPath "pdftoppm"
if ($null -ne $pdfToPpmPath) {
    Add-Check -Name "Poppler pdftoppm" -Ok $true -Detail $pdfToPpmPath
} else {
    Add-Check -Name "Poppler pdftoppm" -Ok $false -Detail "pdftoppm was not found on PATH. Install Poppler and add it to PATH."
}

$configuredJar = if ($env:AUDIVERIS_JAR) {
    $env:AUDIVERIS_JAR
} else {
    Read-PropertiesValue -Path $propertiesPath -Key "audiveris.jar"
}

$configuredJar = Normalize-PathValue -Value $configuredJar

if ([string]::IsNullOrWhiteSpace($configuredJar)) {
    Add-Check -Name "Audiveris JAR" -Ok $false -Detail "AUDIVERIS_JAR or config/audiveris.properties:audiveris.jar is not set."
} elseif (Test-Path -LiteralPath $configuredJar) {
    Add-Check -Name "Audiveris JAR" -Ok $true -Detail (Resolve-Path -LiteralPath $configuredJar).Path
} else {
    Add-Check -Name "Audiveris JAR" -Ok $false -Detail "Configured path does not exist: $configuredJar"
}

$fixturePath = Join-Path $projectRoot "tests\fixtures\sample_score.pdf"
$fixtureExists = Test-Path $fixturePath
Add-Check -Name "Fixture PDF" -Ok $fixtureExists -Detail $fixturePath

foreach ($check in $checks) {
    $status = if ($check.Ok) { "OK" } else { "NG" }
    Write-Output ("[{0}] {1}: {2}" -f $status, $check.Name, $check.Detail)
}

$allPassed = ($checks | Where-Object { -not $_.Ok }).Count -eq 0

if ($allPassed) {
    Write-Output ""
    Write-Output "You can convert the fixture PDF with this command:"
    Write-Output '.\.venv\Scripts\python.exe -m pipeline convert --input tests/fixtures/sample_score.pdf --output .cache/manual-check/sample_score.mid'
    exit 0
}

Write-Output ""
Write-Output "Missing prerequisites prevent end-to-end fixture PDF conversion."
exit 1