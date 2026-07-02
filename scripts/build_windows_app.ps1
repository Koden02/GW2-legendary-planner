[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SourceRoot = Join-Path $ProjectRoot "src"
$EntryPoint = Join-Path $SourceRoot "gw2_legendary_planner\__main__.py"
$SpecPath = Join-Path $ProjectRoot "build\pyinstaller"
$WorkPath = Join-Path $SpecPath "work"
$DistPath = Join-Path $ProjectRoot "dist"
$ExePath = Join-Path $DistPath "gw2planner.exe"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.13 and try again."
}

Set-Location $ProjectRoot
New-Item -ItemType Directory -Path $SpecPath, $WorkPath, $DistPath -Force | Out-Null

$PyInstallerArgs = @(
    "-3.13",
    "-m",
    "uv",
    "run",
    "--group",
    "package",
    "pyinstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--name",
    "gw2planner",
    "--paths",
    $SourceRoot,
    "--collect-data",
    "gw2_legendary_planner",
    "--specpath",
    $SpecPath,
    "--workpath",
    $WorkPath,
    "--distpath",
    $DistPath,
    $EntryPoint
)

& py @PyInstallerArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path $ExePath)) {
    throw "Build finished, but the expected executable was not created: $ExePath"
}

Write-Host "Built $ExePath"
Write-Host "Try: $ExePath gui serve --open --port 0"
