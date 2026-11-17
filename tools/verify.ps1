param(
    [string]$KiCadCli = "$env:LOCALAPPDATA\Programs\KiCad\9.0\bin\kicad-cli.exe",
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $PSScriptRoot
$schematicPath = Join-Path $projectDir 'DRC_POWER2026.ver.0.2.0.kicad_sch'
$documentDir = Join-Path $projectDir 'docs'
if (-not (Test-Path -LiteralPath $KiCadCli)) { throw "Set -KiCadCli to the installed kicad-cli.exe path." }
& $KiCadCli sch erc --format json --severity-all --exit-code-violations --output (Join-Path $documentDir 'ERC.json') $schematicPath
if ($LASTEXITCODE -ne 0) { throw 'ERC reported violations or failed.' }
& $KiCadCli sch erc --format report --severity-all --exit-code-violations --output (Join-Path $documentDir 'ERC.rpt') $schematicPath
if ($LASTEXITCODE -ne 0) { throw 'ERC report failed.' }
& $KiCadCli sch export netlist --format kicadxml --output (Join-Path $documentDir 'main_power.net.xml') $schematicPath
if ($LASTEXITCODE -ne 0) { throw 'Netlist export failed.' }
& $Python (Join-Path $PSScriptRoot 'validate_design.py')
if ($LASTEXITCODE -ne 0) { throw 'Connectivity or footprint audit failed.' }
& $KiCadCli sch export pdf --output (Join-Path $documentDir 'main_power_schematic.pdf') $schematicPath
if ($LASTEXITCODE -ne 0) { throw 'PDF export failed.' }
Write-Output 'ERC, connectivity, footprints and PDF export passed. Inspect changed pages visually after edits.'
