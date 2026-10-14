<#
.SYNOPSIS
    SprintWeave Agent Pipeline — Cursor SDK (Build & Run)

.DESCRIPTION
    Runs SprintWeave agents via Cursor SDK, locally or containerized.

.EXAMPLE
    .\run-agents.ps1 build                      # Build container image
    .\run-agents.ps1 run                         # Full delivery pipeline (container)
    .\run-agents.ps1 run -Pipeline rda           # RDA only (container)
    .\run-agents.ps1 run -Stage RDE-1            # Single stage (container)
    .\run-agents.ps1 local                       # Run locally (no container)
    .\run-agents.ps1 local -Pipeline rda         # Run locally, RDA only

.NOTES
    Requires: CURSOR_API_KEY environment variable
    Get key at: https://cursor.com/dashboard/integrations
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("build", "run", "local", "help")]
    [string]$Command = "help",

    [Alias("p")]
    [ValidateSet("rhoso-delivery", "rda", "rde", "ocp-delivery", "oda", "ode", "full-delivery")]
    [string]$Pipeline = "rhoso-delivery",

    [Alias("s")]
    [string]$Stage,

    [Alias("m")]
    [string]$Model
)

$ErrorActionPreference = "Stop"
$ImageName = "cpat-agents-cursor"
$ImageTag  = "latest"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CpatRoot  = (Resolve-Path "$ScriptDir\..\..").Path

function Test-ApiKey {
    if (-not $env:CURSOR_API_KEY) {
        Write-Host "ERROR: CURSOR_API_KEY is not set." -ForegroundColor Red
        Write-Host "  Get your key at: https://cursor.com/dashboard/integrations"
        Write-Host '  $env:CURSOR_API_KEY = "cursor_..."'
        exit 1
    }
}

function Invoke-Build {
    Write-Host "Building ${ImageName}:${ImageTag}..." -ForegroundColor Cyan
    docker build -f "$ScriptDir\Dockerfile" -t "${ImageName}:${ImageTag}" $CpatRoot
    Write-Host "Build complete: ${ImageName}:${ImageTag}" -ForegroundColor Green
}

function Invoke-ContainerRun {
    Test-ApiKey
    Write-Host "Running CPAT Agent Pipeline (Cursor SDK, containerized)..." -ForegroundColor Cyan

    $dockerArgs = @(
        "run", "--rm",
        "-e", "CURSOR_API_KEY=$env:CURSOR_API_KEY",
        "-e", "CPAT_AGENT_MODEL=$( if ($Model) { $Model } else { 'composer-2.5' })",
        "-v", "${CpatRoot}\output:/workspace/output",
        "${ImageName}:${ImageTag}",
        "--pipeline", $Pipeline
    )
    if ($Stage) {
        $dockerArgs += @("--stage", $Stage)
    }

    & docker @dockerArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "Pipeline complete. Output at: $CpatRoot\output\" -ForegroundColor Green
}

function Invoke-Local {
    Test-ApiKey
    Write-Host "Running CPAT Agent Pipeline (Cursor SDK, local)..." -ForegroundColor Cyan

    $check = python -c "import cursor_sdk" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing cursor-sdk..." -ForegroundColor Cyan
        pip install cursor-sdk
    }

    Push-Location $CpatRoot
    try {
        $pyArgs = @("$ScriptDir\run_pipeline.py", "--pipeline", $Pipeline)
        if ($Stage) { $pyArgs += @("--stage", $Stage) }
        if ($Model) { $pyArgs += @("--model", $Model) }

        python @pyArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }
}

switch ($Command) {
    "build"  { Invoke-Build }
    "run"    { Invoke-ContainerRun }
    "local"  { Invoke-Local }
    "help"   {
        Get-Help $MyInvocation.MyCommand.Path -Detailed
    }
}
