<#
.SYNOPSIS
    SprintWeave Agent Pipeline — Ollama / Local GPU (Build & Run)

.DESCRIPTION
    Runs SprintWeave agents using local open-source LLMs via Ollama.
    No API key required — everything runs on your machine.

.EXAMPLE
    .\run-agents.ps1 build                      # Build container image
    .\run-agents.ps1 run                         # Full delivery pipeline (container + GPU)
    .\run-agents.ps1 run -Pipeline rda           # RDA only (container)
    .\run-agents.ps1 local                       # Run locally (Ollama must be running)
    .\run-agents.ps1 local -Pipeline rda         # Run locally, RDA only
    .\run-agents.ps1 local -Model qwen2.5-coder:7b  # Use a different model

.NOTES
    Prerequisites:
      - Install Ollama: https://ollama.com/download
      - Pull a model: ollama pull qwen2.5-coder:14b
      - pip install openai pyyaml
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("build", "run", "local", "help")]
    [string]$Command = "help",

    [Alias("p")]
    [ValidateSet("rhoso-delivery", "rda", "rde")]
    [string]$Pipeline = "rhoso-delivery",

    [Alias("s")]
    [string]$Stage,

    [Alias("m")]
    [string]$Model = "qwen2.5-coder:14b",

    [string]$ApiBase = "http://localhost:11434/v1"
)

$ErrorActionPreference = "Stop"
$ImageName = "cpat-agents-ollama"
$ImageTag  = "latest"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CpatRoot  = (Resolve-Path "$ScriptDir\..\..").Path

function Invoke-Build {
    Write-Host "Building ${ImageName}:${ImageTag}..." -ForegroundColor Cyan
    docker build -f "$ScriptDir\Dockerfile" -t "${ImageName}:${ImageTag}" $CpatRoot
    Write-Host "Build complete: ${ImageName}:${ImageTag}" -ForegroundColor Green
}

function Invoke-ContainerRun {
    Write-Host "Running CPAT Agent Pipeline (Ollama, containerized)..." -ForegroundColor Cyan

    $dockerArgs = @(
        "run", "--rm", "--gpus", "all",
        "-e", "CPAT_MODEL=$Model",
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
    Write-Host "Running CPAT Agent Pipeline (Ollama, local)..." -ForegroundColor Cyan

    # Check deps
    $check = python -c "import openai" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing dependencies..." -ForegroundColor Cyan
        pip install openai pyyaml
    }

    Push-Location $CpatRoot
    try {
        $pyArgs = @(
            "$ScriptDir\run_pipeline.py",
            "--pipeline", $Pipeline,
            "--model", $Model,
            "--api-base", $ApiBase
        )
        if ($Stage) { $pyArgs += @("--stage", $Stage) }

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
