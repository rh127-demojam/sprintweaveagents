<#
.SYNOPSIS
    SprintWeave Agent Pipeline — Red Hat OpenShift AI (RHOAI)

.DESCRIPTION
    Runs SprintWeave agents against a vLLM model server on RHOAI.
    Targets a remote RHOAI/vLLM inference endpoint (e.g. Llama Stack on OpenShift).

    Uses the shared OpenAI-compatible pipeline runner (agents/ollama/run_pipeline.py)
    with RHOAI-specific defaults and auto-discovery.

.EXAMPLE
    .\run-agents.ps1 run                                     # Full pipeline
    .\run-agents.ps1 run -Pipeline rda                       # RDA only
    .\run-agents.ps1 run -Model "meta-llama/Llama-3.2-3b-instruct"  # Override model
    .\run-agents.ps1 discover                                # Detect endpoint from oc
    .\run-agents.ps1 test                                    # Test connection

.NOTES
    Environment variables:
      RHOAI_API_BASE   — vLLM route URL (auto-detected if oc is logged in)
      RHOAI_API_KEY    — Bearer token (defaults to oc whoami -t)
      RHOAI_MODEL      — Model name override

    Prerequisites:
      - RHOAI environment provisioned (e.g. Llama Stack on OpenShift from RHDP)
      - pip install openai pyyaml
      - oc CLI logged into the cluster (for auto-discovery)
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("run", "discover", "test", "help")]
    [string]$Command = "help",

    [Alias("p")]
    [ValidateSet("rhoso-delivery", "rda", "rde")]
    [string]$Pipeline = "rhoso-delivery",

    [Alias("s")]
    [string]$Stage,

    [Alias("m")]
    [string]$Model,

    [string]$ApiBase
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CpatRoot  = (Resolve-Path "$ScriptDir\..\..").Path
$PipelineRunner = Join-Path $CpatRoot "agents\ollama\run_pipeline.py"

$DefaultModel = "granite32-8b"

# ── Auto-discover vLLM route from OCP cluster ───────────────

function Find-VllmEndpoint {
    # Explicit env / param wins
    if ($ApiBase) { return $ApiBase }
    if ($env:RHOAI_API_BASE) { return $env:RHOAI_API_BASE }

    Write-Host "Auto-discovering vLLM endpoint from OCP cluster..." -ForegroundColor Cyan

    $oc = Get-Command oc -ErrorAction SilentlyContinue
    if (-not $oc) {
        Write-Host "ERROR: 'oc' CLI not found. Set RHOAI_API_BASE manually or install oc." -ForegroundColor Red
        exit 1
    }

    # KServe/RHOAI InferenceService routes land in istio-system;
    # also check the serving namespace and common RHOAI namespaces.
    $namespaces = @("istio-system", "llama-serve", "llama-stack", "rhoai", "redhat-ods-applications", "knative-serving-ingress")
    $route = $null

    foreach ($ns in $namespaces) {
        try {
            $routes = oc get routes -n $ns -o json 2>$null | ConvertFrom-Json
            if ($routes.items) {
                $match = $routes.items | Where-Object {
                    $_.metadata.name -match 'vllm|granite|model-server' -and
                    $_.metadata.name -notmatch 'predictor|istio-ingressgateway'
                } | Select-Object -First 1
                if ($match) {
                    $route = $match.spec.host
                    break
                }
            }
        } catch { }
    }

    if (-not $route) {
        Write-Host "ERROR: Could not auto-discover vLLM route." -ForegroundColor Red
        Write-Host ""
        Write-Host "  Manual steps:"
        Write-Host "    1. oc get routes -A | Select-String vllm"
        Write-Host '    2. $env:RHOAI_API_BASE = "https://<route-host>/v1"'
        Write-Host "    3. Re-run this script"
        exit 1
    }

    $endpoint = "https://${route}/v1"
    Write-Host "Discovered: $endpoint" -ForegroundColor Green
    return $endpoint
}

function Get-ApiKey {
    if ($env:RHOAI_API_KEY) { return $env:RHOAI_API_KEY }

    try {
        $token = oc whoami -t 2>$null
        if ($token) { return $token.Trim() }
    } catch { }

    return "none"
}

# ── Commands ────────────────────────────────────────────────

function Invoke-Discover {
    $endpoint = Find-VllmEndpoint
    Write-Host "vLLM Endpoint: $endpoint" -ForegroundColor Green
    Write-Host ""
    Write-Host "Set it permanently:"
    Write-Host "  `$env:RHOAI_API_BASE = `"$endpoint`""
}

function Invoke-Test {
    $endpoint = Find-VllmEndpoint
    $apiKey   = Get-ApiKey
    $mdl      = if ($Model) { $Model } elseif ($env:RHOAI_MODEL) { $env:RHOAI_MODEL } else { $DefaultModel }

    Write-Host "Testing connection to RHOAI..." -ForegroundColor Cyan
    Write-Host "  Endpoint: $endpoint"
    Write-Host "  Model:    $mdl"
    Write-Host ""

    # Test /v1/models (use curl.exe to handle self-signed TLS certs)
    Write-Host "Listing available models..." -ForegroundColor Cyan
    try {
        if ($apiKey -ne "none") {
            $raw = curl.exe -sk "$endpoint/models" -H "Authorization: Bearer $apiKey" 2>$null
        } else {
            $raw = curl.exe -sk "$endpoint/models" 2>$null
        }
        $response = $raw | ConvertFrom-Json
        Write-Host "Available models:" -ForegroundColor Green
        foreach ($m in $response.data) {
            Write-Host "  - $($m.id)"
        }
    } catch {
        Write-Host "ERROR: Could not reach $endpoint/models" -ForegroundColor Red
        Write-Host "  $raw"
        exit 1
    }

    # Test inference (write JSON to temp file to avoid PowerShell quote-stripping)
    Write-Host ""
    Write-Host "Testing inference..." -ForegroundColor Cyan
    try {
        $tmpFile = [System.IO.Path]::GetTempFileName()
        $payload = '{"model":"' + $mdl + '","messages":[{"role":"user","content":"Say hello in one word."}],"max_tokens":10}'
        [System.IO.File]::WriteAllText($tmpFile, $payload)
        if ($apiKey -ne "none") {
            $raw = curl.exe -sk "$endpoint/chat/completions" -H "Content-Type: application/json" -H "Authorization: Bearer $apiKey" -d "@$tmpFile" 2>$null
        } else {
            $raw = curl.exe -sk "$endpoint/chat/completions" -H "Content-Type: application/json" -d "@$tmpFile" 2>$null
        }
        Remove-Item $tmpFile -ErrorAction SilentlyContinue
        $resp = $raw | ConvertFrom-Json
        $reply = $resp.choices[0].message.content
        Write-Host "  Model responded: $reply" -ForegroundColor Green
        Write-Host "Inference working! Ready for SprintWeave pipeline." -ForegroundColor Green
    } catch {
        Remove-Item $tmpFile -ErrorAction SilentlyContinue
        Write-Host "WARNING: Inference test failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

function Invoke-Run {
    $endpoint = Find-VllmEndpoint
    $apiKey   = Get-ApiKey
    $mdl      = if ($Model) { $Model } elseif ($env:RHOAI_MODEL) { $env:RHOAI_MODEL } else { $DefaultModel }

    Write-Host "Running SprintWeave Agent Pipeline (RHOAI)..." -ForegroundColor Cyan
    Write-Host "  Endpoint: $endpoint"
    Write-Host "  Model:    $mdl"
    Write-Host ""

    # Check deps
    $check = python -c "import openai" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing dependencies..." -ForegroundColor Cyan
        pip install openai pyyaml
    }

    Push-Location $CpatRoot
    try {
        $pyArgs = @(
            $PipelineRunner,
            "--pipeline", $Pipeline,
            "--model", $mdl,
            "--api-base", $endpoint,
            "--api-key", $apiKey
        )
        if ($Stage) { $pyArgs += @("--stage", $Stage) }

        python @pyArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }
}

# ── Entrypoint ──────────────────────────────────────────────

switch ($Command) {
    "run"       { Invoke-Run }
    "discover"  { Invoke-Discover }
    "test"      { Invoke-Test }
    "help"      { Get-Help $MyInvocation.MyCommand.Path -Detailed }
}
