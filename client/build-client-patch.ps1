# Builds patch-Z.mpq for the Necromancer class from your own client DBCs.
#
# Requirements: the wow_dbc_patcher fork (packed-DBC support):
#   https://github.com/11Marlowe/twow-raid-visuals
# Build it once with `cargo build --release`; pass the exe path below.
#
# Usage:
#   .\build-client-patch.ps1 -ClientDbcDir "C:\path\to\TWoWClient\Game\dbc" `
#                            -PatcherExe   "C:\path\to\wow_dbc_patcher.exe"
#
# Output: <script dir>\build\patch-Z.mpq (+ the patched DBCs next to it).
# Install: copy patch-Z.mpq into the client's Data\ folder and copy
# build\ChrClasses.dbc into the server's dbc\ folder.

param(
    [Parameter(Mandatory = $true)][string]$ClientDbcDir,
    [Parameter(Mandatory = $true)][string]$PatcherExe,
    [string]$SchemaDir = "",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $SchemaDir) {
    # the patcher's cargo layout keeps the schemas at the repo root
    # (<repo>\schema), i.e. two levels above target\release\*.exe
    $candidates = @(
        (Join-Path (Split-Path -Parent $PatcherExe) "schema"),
        (Join-Path (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PatcherExe))) "schema")
    )
    $SchemaDir = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $SchemaDir) {
        throw "Schema directory not found next to the patcher; pass -SchemaDir explicitly."
    }
}
if (-not $OutDir) {
    $OutDir = Join-Path $PSScriptRoot "build"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$dbcFiles = @(
    "ChrClasses.dbc", "CharBaseInfo.dbc", "CharStartOutfit.dbc",
    "Spell.dbc", "SkillLine.dbc", "SkillLineAbility.dbc", "SkillRaceClassInfo.dbc"
)
$patchFiles = Get-ChildItem (Join-Path $PSScriptRoot "patches\*.yaml") | Sort-Object Name

$arguments = @("build")
foreach ($dbc in $dbcFiles) {
    $arguments += @("--dbc-files", (Join-Path $ClientDbcDir $dbc))
}
foreach ($patch in $patchFiles) {
    $arguments += @("--patches", $patch.FullName)
}
$arguments += @(
    "--schema-dir", $SchemaDir,
    "--out-dir", $OutDir,
    "--includes-dir", (Join-Path $PSScriptRoot "includes"),
    "--mpq-version", "1",
    "--mpq", (Join-Path $OutDir "patch-Z.mpq")
)

& $PatcherExe @arguments
if ($LASTEXITCODE -ne 0) {
    throw "wow_dbc_patcher failed with exit code $LASTEXITCODE - patch-Z.mpq was NOT (re)built, do not deploy."
}

Write-Host ""
Write-Host "Built: $OutDir\patch-Z.mpq"
Write-Host "Install: copy patch-Z.mpq to the client's Data\ folder;"
Write-Host "         copy $OutDir\ChrClasses.dbc to the server's dbc\ folder."
Write-Host ""
Write-Host "zhCN clients: also append the CLASS_NECROMANCER line to the loose"
Write-Host "  Data\GlueStrings.lua (see client\README.md)."
