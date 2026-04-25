# Demo Data

Sample data for testing the Research OS without private research content.

## Contents

### papers/
Sample paper directories with metadata JSON files.
Use `scholaraio benchmark` to verify indexing works with these.

### workspace/
Sample workspace with a small paper subset for testing search, topics, and export.

### generated/
Sample Level V status products:
- `system_manifest.json` — example system state snapshot
- `system_health.json` — example health check output
- `recommended_actions.json` — example repair suggestions

## Usage

Run bootstrap with demo data:
```powershell
.\bootstrap.ps1 -WithDemoData
```

This copies demo papers and workspace into your local `data/` and `workspace/` directories.
