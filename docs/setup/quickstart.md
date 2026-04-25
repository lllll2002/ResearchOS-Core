# Quickstart

## Prerequisites

- Windows 10/11 (PowerShell 5.1+)
- Python 3.10+
- Git

## Steps

### 1. Clone

```powershell
git clone <repo-url>
cd research-os-core
```

### 2. Bootstrap

```powershell
# With demo data (recommended for first run)
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 -WithDemoData
```

### 3. Install

```powershell
pip install -e .
```

### 4. Configure

Edit `config.local.yaml` with your API keys.

### 5. Verify

```bash
scholaraio --help
scholaraio benchmark
```

### 6. Optional: Level V Operations

```powershell
# Manual health check
powershell -ExecutionPolicy Bypass -File .\scripts\run_health_daemon.ps1

# Register scheduled tasks (requires Administrator)
powershell -ExecutionPolicy Bypass -File .\scripts\register_health_daemon_tasks.ps1
```
