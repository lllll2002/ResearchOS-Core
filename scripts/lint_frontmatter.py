"""
lint_frontmatter.py — Frontmatter linter for Obsidian Research Vault.

Usage:
    python lint_frontmatter.py check [--scope spine|full]
    python lint_frontmatter.py fix --scope spine
    python lint_frontmatter.py strict
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

import os
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT = Path(os.environ.get("RESEARCH_OS_VAULT", PROJECT_ROOT / "vault"))
RULES_PATH = PROJECT_ROOT / "scripts" / "system_rules.yaml"
OUTPUT_DIR = PROJECT_ROOT / "generated"

SPINE_PATTERNS = [
    "00_intro.md",
    "00_Overview/*.md",
    "01_Planning/AI_active_context.md",
    "01_Planning/today.md",
    "01_Planning/wiki_hub.md",
    "02_Research_Projects/*/wiki/claims.md",
    "02_Research_Projects/*/wiki/index.md",
    "03_Theoretical_Work/*/wiki/index.md",
    "07_System_Optimization/*.md",
]


def load_schemas():
    if RULES_PATH.exists():
        with open(RULES_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f).get("schemas", {})
    return {}


def match_schema(rel_path: str, schemas: dict):
    for name, schema in schemas.items():
        for pattern in schema.get("match", []):
            if Path(rel_path).match(pattern):
                return name, schema
    return None, None


def parse_frontmatter(text: str):
    if not text.startswith("---"):
        return None, text, "No frontmatter"
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", text, re.DOTALL)
    if not m:
        return None, text, "Unclosed frontmatter"
    try:
        fm = yaml.safe_load(m.group(1))
        if not isinstance(fm, dict):
            return None, m.group(2), "Frontmatter is not a dict"
        return fm, m.group(2), None
    except yaml.YAMLError as e:
        return None, text, f"YAML error: {e}"


def check_file(path: Path, schemas: dict):
    rel = path.relative_to(VAULT).as_posix()
    name, schema = match_schema(rel, schemas)
    if not schema:
        return {"file": rel, "schema": None, "issues": [], "skipped": True}

    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body, err = parse_frontmatter(text)

    issues = []
    if err:
        issues.append(f"PARSE: {err}")
        return {"file": rel, "schema": name, "issues": issues, "fm": None, "body": body}

    # Required fields
    for field in schema.get("required", []):
        if field not in fm or fm[field] is None:
            issues.append(f"MISSING: {field}")

    # Status validation
    valid = schema.get("status_values", [])
    if valid and "status" in fm and fm["status"] not in valid:
        issues.append(f"BAD_STATUS: '{fm['status']}' not in {valid}")

    # Claims body checks
    if name == "claims_register" and "body_checks" in schema:
        bc = schema["body_checks"]
        ids = re.findall(bc.get("claim_id_pattern", ""), body, re.MULTILINE)
        if not ids:
            issues.append("CLAIMS: No claim IDs found")
        dupes = [x for x in set(ids) if ids.count(x) > 1]
        if dupes:
            issues.append(f"CLAIMS: Duplicate IDs: {dupes}")

    return {"file": rel, "schema": name, "issues": issues, "fm": fm, "body": body}


def fix_file(path: Path, result: dict, schema: dict):
    if result.get("skipped"):
        return False

    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body, err = parse_frontmatter(text)
    changed = False

    if fm is None:
        fm = {}
        changed = True

    for field in schema.get("required", []):
        if field not in fm or fm[field] is None:
            if field == "title":
                fm[field] = path.stem
            elif field in ("updated", "date"):
                fm[field] = date.today().isoformat()
            elif field == "tags":
                fm[field] = []
            elif field == "status":
                fm[field] = "TBD"
            else:
                fm[field] = None
            changed = True

    if changed:
        yml = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
        new_text = f"---\n{yml}\n---\n{body}"
        path.write_text(new_text, encoding="utf-8")

    return changed


def get_files(scope: str):
    if scope == "spine":
        files = []
        for p in SPINE_PATTERNS:
            files.extend(VAULT.glob(p))
        return sorted(set(files))
    return sorted(VAULT.rglob("*.md"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["check", "fix", "strict"])
    parser.add_argument("--scope", default="spine", choices=["spine", "full"])
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    schemas = load_schemas()
    files = get_files(args.scope)

    results = []
    errors = 0
    fixed = 0

    for f in files:
        r = check_file(f, schemas)
        if r.get("skipped"):
            continue

        if args.mode == "fix" and r["issues"]:
            _, schema = match_schema(r["file"], schemas)
            if schema and fix_file(f, r, schema):
                r["issues"].append("FIXED: minimal fields added")
                fixed += 1

        if r["issues"]:
            errors += len([i for i in r["issues"] if not i.startswith("FIXED")])
        results.append(r)

    # Report
    lines = [
        "# Frontmatter Lint Report",
        f"",
        f"- Date: {date.today().isoformat()}",
        f"- Mode: {args.mode} | Scope: {args.scope}",
        f"- Files checked: {len(results)}",
        f"- Issues: {errors} | Fixed: {fixed}",
        "",
    ]
    for r in results:
        if not r["issues"]:
            continue
        lines.append(f"## {r['file']} [{r['schema']}]")
        for i in r["issues"]:
            lines.append(f"- {i}")
        lines.append("")

    if not any(r["issues"] for r in results):
        lines.append("All checked files pass.\n")

    report = "\n".join(lines)
    out_path = OUTPUT_DIR / "frontmatter_lint_report.md"
    out_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nSaved to: {out_path}")

    if args.mode == "strict" and errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
