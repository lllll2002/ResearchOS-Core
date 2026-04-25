"""
generate_system_manifest.py — System status snapshot.

Outputs JSON + Markdown to 07_System_Optimization/generated/.

Usage:
    python generate_system_manifest.py
"""

import json
import re
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

import os
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT = Path(os.environ.get("RESEARCH_OS_VAULT", PROJECT_ROOT / "vault"))
SA_ROOT = PROJECT_ROOT
OUTPUT_DIR = PROJECT_ROOT / "generated"


def count_dirs(path: Path) -> int:
    if not path.exists():
        return 0
    return len([d for d in path.iterdir() if d.is_dir()])


def file_info(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "size": 0}
    return {"exists": True, "size": path.stat().st_size}


def db_counts(db_path: Path) -> dict:
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(db_path)
    try:
        papers = conn.execute("SELECT COUNT(*) FROM papers_registry").fetchone()[0]
        chunks = conn.execute("SELECT COUNT(*) FROM paper_chunks").fetchone()[0]
        vectors = conn.execute("SELECT COUNT(*) FROM paper_vectors").fetchone()[0]
        return {"papers": papers, "chunks": chunks, "vectors": vectors}
    except Exception:
        return {}
    finally:
        conn.close()


def mcp_tool_count() -> int:
    mcp = SA_ROOT / "scholaraio" / "mcp_server.py"
    if not mcp.exists():
        return 0
    return mcp.read_text(encoding="utf-8").count("@mcp.tool")


def benchmark_score() -> float | None:
    f = SA_ROOT / "data" / "benchmark_latest.md"
    if not f.exists():
        return None
    m = re.search(r"(\d+)%", f.read_text(encoding="utf-8"))
    return int(m.group(1)) / 100 if m else None


def git_status() -> dict:
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=VAULT,
                           capture_output=True, text=True, timeout=10)
        lines = [l for l in r.stdout.strip().split("\n") if l]
        return {"uncommitted": len(lines)}
    except Exception:
        return {"uncommitted": None}


def generate():
    db = SA_ROOT / "data" / "index.db"
    counts = db_counts(db)
    kg = file_info(SA_ROOT / "data" / "kg.json")

    # KG details
    kg_details = {"exists": kg["exists"], "size": kg["size"], "status": "empty" if kg["size"] < 100 else "ok"}
    if kg["exists"] and kg["size"] > 100:
        import json as _json
        try:
            kg_data = _json.loads((SA_ROOT / "data" / "kg.json").read_text("utf-8"))
            kg_details["entities"] = len(kg_data.get("entities", {}))
            kg_details["relations"] = len(kg_data.get("relations", []))
            kg_details["last_built"] = datetime.fromtimestamp(
                (SA_ROOT / "data" / "kg.json").stat().st_mtime
            ).isoformat()[:19]
        except Exception:
            pass

    # Backup status
    backup_log = Path(os.environ.get("RESEARCH_OS_BACKUP_LOG", PROJECT_ROOT / "backups" / "backup_log.txt"))
    backup_status = {"configured": backup_log.parent.exists()}
    if backup_log.exists():
        lines = backup_log.read_text("utf-8").strip().split("\n")
        if lines:
            backup_status["last_run"] = lines[-1].split("|")[0].strip()
            backup_status["total_runs"] = len(lines)

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "vault": {
            "templates": count_dirs(VAULT / "_templates") + len(list((VAULT / "_templates").glob("*.md"))) if (VAULT / "_templates").exists() else 0,
            "snippets": len(list((VAULT / ".obsidian" / "snippets").glob("*.css"))) if (VAULT / ".obsidian" / "snippets").exists() else 0,
            "skills": count_dirs(VAULT / ".claude" / "skills"),
            "entry_pages": {
                "00_intro": (VAULT / "00_intro.md").exists(),
                "AI_active_context": (VAULT / "01_Planning" / "AI_active_context.md").exists(),
                "wiki_hub": (VAULT / "01_Planning" / "wiki_hub.md").exists(),
            },
        },
        "scholaraio": {
            "papers": counts.get("papers", 0),
            "chunks": counts.get("chunks", 0),
            "vectors": counts.get("vectors", 0),
            "pending": count_dirs(SA_ROOT / "data" / "pending"),
            "mcp_tools": mcp_tool_count(),
            "index_db_mb": round(file_info(db)["size"] / 1024 / 1024, 1),
            "faiss_index": file_info(SA_ROOT / "data" / "faiss.index"),
            "kg": kg_details,
            "backup": backup_status,
            "benchmark_score": benchmark_score(),
        },
        "git": git_status(),
    }
    return manifest


def to_markdown(m: dict) -> str:
    sa = m["scholaraio"]
    v = m["vault"]
    g = m["git"]

    kg_status = sa.get("kg", {}).get("status", "unknown")
    bench = f"{sa['benchmark_score']:.0%}" if sa["benchmark_score"] else "N/A"
    uncommitted = g.get("uncommitted", "?")

    return f"""# System Manifest

Generated: {m['generated_at'][:19]}

## Vault
- Skills: {v['skills']}
- Templates: {v['templates']}
- Snippets: {v['snippets']}
- Entry pages: {'all present' if all(v['entry_pages'].values()) else 'MISSING: ' + str([k for k, v in v['entry_pages'].items() if not v])}

## ScholarAIO
- Papers: {sa['papers']}
- Chunks: {sa['chunks']}
- Vectors: {sa['vectors']}
- Pending: {sa['pending']}
- MCP tools: {sa['mcp_tools']}
- Index DB: {sa['index_db_mb']} MB
- FAISS: {'present' if sa['faiss_index']['exists'] else 'MISSING'}
- KG: {kg_status} ({sa.get('kg', {}).get('size', 0)} bytes, {sa.get('kg', {}).get('entities', '?')} entities, {sa.get('kg', {}).get('relations', '?')} relations)
- Benchmark: {bench}

## Git
- Uncommitted changes: {uncommitted}

## Backup
- Configured: {sa.get('backup', {}).get('configured', False)}
- Last run: {sa.get('backup', {}).get('last_run', 'never')}
- Total runs: {sa.get('backup', {}).get('total_runs', 0)}

## Health Flags
{f'- WARNING: KG is empty, run `scholaraio kg build`' if kg_status == 'empty' else f'- KG: OK ({sa.get("kg", {}).get("entities", "?")} entities)'}
{f'- WARNING: {uncommitted} uncommitted files' if isinstance(uncommitted, int) and uncommitted > 50 else '- Git: clean' if uncommitted == 0 else f'- Git: {uncommitted} changes'}
{f'- WARNING: Benchmark below 80%' if sa['benchmark_score'] and sa['benchmark_score'] < 0.8 else '- Benchmark: OK' if sa['benchmark_score'] else '- Benchmark: not run'}
{f'- WARNING: {sa.get("pending", 0)} pending papers' if sa.get('pending', 0) > 100 else f'- Pending: {sa.get("pending", 0)}'}
"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    m = generate()

    json_path = OUTPUT_DIR / "system_manifest.json"
    md_path = OUTPUT_DIR / "system_manifest.md"

    json_path.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(to_markdown(m), encoding="utf-8")

    print(to_markdown(m))
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()
