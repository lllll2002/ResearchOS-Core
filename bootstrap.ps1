param(
    [string]$VaultPath = ".\vault",
    [string]$DataPath = ".\data",
    [switch]$WithDemoData,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Ensure-Dir($path) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        Write-Host "  Created: $path"
    }
}

# --- Step 1: Check repo root ---
Write-Step "Checking repository root"
$required = @("pyproject.toml", "scholaraio", "scripts", "vault-template", "config.yaml.example")
foreach ($item in $required) {
    if (-not (Test-Path $item)) {
        throw "Missing required path: $item. Run bootstrap.ps1 from the repo root."
    }
}
Write-Host "  Repository root verified."

# --- Step 2: Create local directories ---
Write-Step "Preparing local directories"
Ensure-Dir $VaultPath
Ensure-Dir $DataPath
Ensure-Dir ".\workspace"
Ensure-Dir ".\backups"
Ensure-Dir ".\logs"
Ensure-Dir ".\generated"

# --- Step 3: Initialize config ---
Write-Step "Initializing configuration"
if ((-not (Test-Path ".\config.yaml")) -or $Force) {
    Copy-Item ".\config.yaml.example" ".\config.yaml" -Force
    Write-Host "  Initialized config.yaml from config.yaml.example"
} else {
    Write-Host "  config.yaml already exists, skipped"
}

if (-not (Test-Path ".\config.local.yaml")) {
    @"
# config.local.yaml - Local overrides (not tracked by git)
# Fill in your own API keys and paths here.

llm:
  api_key: ""

embed:
  source: "huggingface"

# Optional: override default vault path
# vault_path: "C:/path/to/your/vault"
"@ | Set-Content ".\config.local.yaml" -Encoding UTF8
    Write-Host "  Created config.local.yaml placeholder"
} else {
    Write-Host "  config.local.yaml already exists, skipped"
}

# --- Step 4: Initialize vault from template ---
Write-Step "Initializing vault from template"
$vaultMarker = Join-Path $VaultPath ".vault_initialized"
if ((-not (Test-Path $vaultMarker)) -or $Force) {
    Copy-Item ".\vault-template\*" $VaultPath -Recurse -Force
    Set-Content $vaultMarker "initialized $(Get-Date -Format s)"
    Write-Host "  Vault template copied to $VaultPath"
} else {
    Write-Host "  Vault already initialized, skipped"
}

# --- Step 5: Install demo data ---
if ($WithDemoData) {
    Write-Step "Installing demo data"
    if (Test-Path ".\demo-data\papers") {
        Ensure-Dir ".\data\papers"
        Copy-Item ".\demo-data\papers\*" ".\data\papers" -Recurse -Force
        Write-Host "  Demo papers copied"
    }
    if (Test-Path ".\demo-data\workspace") {
        Copy-Item ".\demo-data\workspace\*" ".\workspace" -Recurse -Force
        Write-Host "  Demo workspace copied"
    }
    if (Test-Path ".\demo-data\generated") {
        Ensure-Dir ".\generated"
        Copy-Item ".\demo-data\generated\*" ".\generated" -Recurse -Force
        Write-Host "  Demo status products copied"
    }
}

# --- Step 6: Check Python ---
Write-Step "Checking Python"
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Python detected: $pythonVersion"
} catch {
    Write-Warning "Python not found in PATH. Install Python 3.10+ before continuing."
}

try {
    python -c "import scholaraio; print('  scholaraio package: OK')" 2>$null
} catch {
    Write-Host "  scholaraio not installed yet. Run: pip install -e ." -ForegroundColor Yellow
}

# --- Step 7: Next steps ---
Write-Step "Bootstrap complete"
Write-Host @"

  Next steps:

  1. Install the package (if not already):
     pip install -e .

  2. Edit your local config:
     config.local.yaml

  3. Verify the CLI:
     scholaraio --help

  4. Run a benchmark (requires demo data or real papers):
     scholaraio benchmark

  5. Optional - start Level V health monitoring:
     powershell -ExecutionPolicy Bypass -File .\scripts\run_health_daemon.ps1

  6. Optional - register scheduled tasks (Administrator required):
     powershell -ExecutionPolicy Bypass -File .\scripts\register_health_daemon_tasks.ps1

"@
