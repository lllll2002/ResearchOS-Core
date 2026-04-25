"""
kgraph.py — 个人知识图谱关系索引
==================================

扫描 Obsidian vault 中的 Markdown 文件，提取实体和关系：
- YAML frontmatter 中的结构化关系字段
- Obsidian [[wikilinks]]
- Claim 表格中的引用关系

生成可查询的关系索引，支持：
- "哪些实验支持 C-003？"
- "G3BP1 相关的所有论文和实验"
- "跨项目知识关联"

用法：
    from scholaraio.kgraph import build_graph, query_entity
    g = build_graph(vault_path)
    results = query_entity(g, "C-003")
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Entity and Relation data structures
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    """A node in the knowledge graph."""
    id: str                     # Canonical identifier (e.g., "C-003", "EXP-002", "BC-045")
    type: str                   # claim | experiment | paper | evidence | model | synthesis | reagent | concept | file
    label: str                  # Human-readable label
    source_file: str            # File where this entity is defined
    metadata: dict = field(default_factory=dict)


@dataclass
class Relation:
    """A directed edge in the knowledge graph."""
    source: str                 # Entity ID
    target: str                 # Entity ID or raw reference
    relation: str               # supports | refutes | uses | cites | links_to | contains | part_of
    context: str = ""           # Brief context from source
    source_file: str = ""


@dataclass
class KnowledgeGraph:
    """In-memory knowledge graph."""
    entities: dict[str, Entity] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity

    def add_relation(self, relation: Relation) -> None:
        self.relations.append(relation)

    def query(self, entity_id: str) -> dict:
        """Find all relations involving an entity."""
        outgoing = [r for r in self.relations if r.source == entity_id]
        incoming = [r for r in self.relations if r.target == entity_id]
        entity = self.entities.get(entity_id)
        return {
            "entity": asdict(entity) if entity else None,
            "outgoing": [asdict(r) for r in outgoing],
            "incoming": [asdict(r) for r in incoming],
        }

    def search(self, keyword: str) -> list[dict]:
        """Search entities by keyword in id or label."""
        kw = keyword.lower()
        hits = []
        for e in self.entities.values():
            if kw in e.id.lower() or kw in e.label.lower():
                hits.append(asdict(e))
        return hits

    def stats(self) -> dict:
        """Return graph statistics."""
        type_counts: dict[str, int] = {}
        for e in self.entities.values():
            type_counts[e.type] = type_counts.get(e.type, 0) + 1
        rel_counts: dict[str, int] = {}
        for r in self.relations:
            rel_counts[r.relation] = rel_counts.get(r.relation, 0) + 1
        return {
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "entity_types": type_counts,
            "relation_types": rel_counts,
        }

    def to_json(self) -> str:
        return json.dumps({
            "entities": {k: asdict(v) for k, v in self.entities.items()},
            "relations": [asdict(r) for r in self.relations],
        }, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------

# Claim pattern: ## C-NNN: <title>
_CLAIM_RE = re.compile(r"^##\s+(C-\d{3}):\s+(.+)", re.MULTILINE)

# Experiment pattern: EXP-NNN
_EXP_RE = re.compile(r"\b(EXP-\d{3})\b")

# Paper ID pattern: BC-NNN or similar project prefixes
_PAPER_ID_RE = re.compile(r"\b(BC-\d{3}|PS-\d{3}|MEA-\d{3})\b")

# Wikilink pattern: [[target]] or [[target|alias]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# YAML frontmatter extraction
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# Claim table row: evidence basis containing references
_EVIDENCE_REF_RE = re.compile(
    r"(?:EXP-\d{3}|frap\d*\.nd2|recover\d+.*?\.nd2|\d+\.\d+/[\w.-]+|"
    r"DiSBAC|BAPTA-AM|NaAsO2|G3BP1|RHS2116)"
)

# Frontmatter relation fields (standardized)
_RELATION_FIELDS = {
    "related_papers": "cites",
    "supports_claim": "supports",
    "refutes_claim": "refutes",
    "uses_reagent": "uses",
    "uses_equipment": "uses",
    "part_of": "part_of",
    "depends_on": "depends_on",
    "blocks": "blocks",
}


def _parse_yaml_simple(text: str) -> dict:
    """Minimal YAML parser for frontmatter (key: value pairs only)."""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # Handle YAML lists (inline [a, b] or bare comma-separated)
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
            result[key] = val
    return result


def _extract_claims(content: str, filepath: str, graph: KnowledgeGraph) -> None:
    """Extract claim entities and their evidence relations."""
    for m in _CLAIM_RE.finditer(content):
        claim_id = m.group(1)
        claim_title = m.group(2).strip()

        # Find the claim's table block (between this heading and the next ---)
        start = m.end()
        next_heading = content.find("\n## ", start)
        block = content[start:next_heading] if next_heading != -1 else content[start:]

        # Extract status
        status_match = re.search(r"\*\*Status\*\*\s*\|\s*`(\w+)`", block)
        status = status_match.group(1) if status_match else "unknown"

        graph.add_entity(Entity(
            id=claim_id, type="claim", label=claim_title,
            source_file=filepath,
            metadata={"status": status},
        ))

        # Extract evidence references from the block
        for exp_m in _EXP_RE.finditer(block):
            exp_id = exp_m.group(1)
            graph.add_relation(Relation(
                source=exp_id, target=claim_id,
                relation="supports", context=f"evidence in {claim_id} block",
                source_file=filepath,
            ))

        # Extract wikilinks as relations
        for wl in _WIKILINK_RE.finditer(block):
            target = wl.group(1)
            graph.add_relation(Relation(
                source=claim_id, target=target,
                relation="links_to", context="claim reference",
                source_file=filepath,
            ))


def _extract_experiments(content: str, filepath: str, graph: KnowledgeGraph) -> None:
    """Extract experiment entity references."""
    for m in _EXP_RE.finditer(content):
        exp_id = m.group(1)
        if exp_id not in graph.entities:
            graph.add_entity(Entity(
                id=exp_id, type="experiment", label=exp_id,
                source_file=filepath,
            ))


def _extract_wikilinks(content: str, filepath: str, graph: KnowledgeGraph) -> None:
    """Extract wikilink relations from file."""
    # Create a file entity
    file_id = Path(filepath).stem
    for m in _WIKILINK_RE.finditer(content):
        target = m.group(1)
        graph.add_relation(Relation(
            source=file_id, target=target,
            relation="links_to", source_file=filepath,
        ))


def _extract_frontmatter_relations(content: str, filepath: str, graph: KnowledgeGraph) -> None:
    """Extract structured relations from YAML frontmatter."""
    fm_match = _FRONTMATTER_RE.match(content)
    if not fm_match:
        return

    fm = _parse_yaml_simple(fm_match.group(1))
    file_id = Path(filepath).stem

    for fm_key, rel_type in _RELATION_FIELDS.items():
        if fm_key in fm:
            targets = fm[fm_key]
            if isinstance(targets, str):
                targets = [targets]
            for target in targets:
                if target:
                    graph.add_relation(Relation(
                        source=file_id, target=target,
                        relation=rel_type, context=f"frontmatter:{fm_key}",
                        source_file=filepath,
                    ))


def _extract_paper_ids(content: str, filepath: str, graph: KnowledgeGraph) -> None:
    """Extract project paper IDs (BC-NNN, PS-NNN, etc.)."""
    for m in _PAPER_ID_RE.finditer(content):
        pid = m.group(1)
        if pid not in graph.entities:
            graph.add_entity(Entity(
                id=pid, type="paper_ref", label=pid,
                source_file=filepath,
            ))


# ---------------------------------------------------------------------------
# LLM entity extraction
# ---------------------------------------------------------------------------

_LLM_EXTRACT_SYSTEM = """\
You are a scientific knowledge graph entity extractor.
Given a paper's title, abstract, and/or conclusion, extract:
1. Key scientific entities (methods, materials, organisms, devices, phenomena, metrics)
2. Relationships between entities

Output a JSON object:
{
  "entities": [
    {"id": "<short_id>", "type": "<method|material|organism|device|phenomenon|metric>", "label": "<name>"}
  ],
  "relations": [
    {"source": "<entity_id>", "target": "<entity_id>", "relation": "<uses|measures|produces|inhibits|activates|contains|compared_to>"}
  ]
}

Rules:
- Keep entity IDs short and lowercase (e.g., "g3bp1", "mea_array", "patch_clamp")
- Extract 5-15 entities per paper, focus on the most important ones
- Only extract relations that are explicitly stated or strongly implied
- Output valid JSON only, no markdown
"""


def extract_entities_llm(
    paper_id: str,
    title: str,
    abstract: str,
    conclusion: str,
    cfg: "Config",
) -> tuple[list[Entity], list[Relation]]:
    """Use LLM to extract entities and relations from paper metadata.

    Args:
        paper_id: Paper UUID or directory name.
        title: Paper title.
        abstract: Paper abstract text.
        conclusion: Paper conclusion text.
        cfg: Config with LLM settings.

    Returns:
        Tuple of (entities, relations) extracted from the paper.
    """
    from scholaraio.metrics import call_llm

    text_parts = [f"Title: {title}"]
    if abstract:
        text_parts.append(f"Abstract: {abstract[:1500]}")
    if conclusion:
        text_parts.append(f"Conclusion: {conclusion[:1000]}")
    prompt = "\n\n".join(text_parts)

    try:
        result = call_llm(
            prompt, cfg,
            system=_LLM_EXTRACT_SYSTEM,
            json_mode=True,
            max_tokens=1000,
            purpose="kg_extract",
        )
        resp = json.loads(result.content)
    except Exception as exc:
        _log.warning("LLM extraction failed for %s: %s", paper_id, exc)
        return [], []

    entities = []
    for e in resp.get("entities", []):
        eid = f"{paper_id}::{e.get('id', 'unknown')}"
        entities.append(Entity(
            id=eid,
            type=e.get("type", "concept"),
            label=e.get("label", ""),
            source_file=paper_id,
            metadata={"paper_id": paper_id},
        ))

    relations = []
    for r in resp.get("relations", []):
        relations.append(Relation(
            source=f"{paper_id}::{r.get('source', '')}",
            target=f"{paper_id}::{r.get('target', '')}",
            relation=r.get("relation", "related_to"),
            context=f"LLM extracted from {title[:60]}",
            source_file=paper_id,
        ))

    return entities, relations


def enrich_graph_llm(
    graph: KnowledgeGraph,
    papers_dir: Path,
    cfg: "Config",
    *,
    max_papers: int = 50,
) -> int:
    """Enrich a knowledge graph with LLM-extracted entities from papers.

    Reads meta.json from each paper directory and extracts entities/relations
    from title + abstract + conclusion.

    Args:
        graph: Existing graph to enrich.
        papers_dir: Directory containing paper subdirectories.
        cfg: Config with LLM settings.
        max_papers: Maximum papers to process (LLM cost control).

    Returns:
        Number of new entities added.
    """
    count = 0
    processed = 0

    if not papers_dir.exists():
        return 0

    for pdir in sorted(papers_dir.iterdir()):
        if not pdir.is_dir() or pdir.name.startswith("."):
            continue
        meta_path = pdir / "meta.json"
        if not meta_path.exists():
            continue

        if processed >= max_papers:
            break

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        paper_id = meta.get("id", pdir.name)
        title = meta.get("title", "")
        abstract = meta.get("abstract", "")
        conclusion = meta.get("l3_conclusion", "")

        if not title:
            continue

        # Skip if already extracted for this paper
        if any(e.metadata.get("paper_id") == paper_id for e in graph.entities.values()):
            continue

        _log.info("LLM extracting from: %s", title[:60])
        entities, relations = extract_entities_llm(
            paper_id, title, abstract, conclusion, cfg,
        )

        for e in entities:
            graph.add_entity(e)
            count += 1
        for r in relations:
            graph.add_relation(r)

        processed += 1

    _log.info("LLM enrichment: %d entities from %d papers", count, processed)
    return count


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(
    vault_path: Path,
    scan_dirs: list[str] | None = None,
) -> KnowledgeGraph:
    """Build a knowledge graph from Obsidian vault files.

    Args:
        vault_path: Root of the Obsidian vault.
        scan_dirs: Subdirectories to scan (relative to vault).
            Defaults to wiki, experiment, and planning directories.

    Returns:
        Populated KnowledgeGraph instance.
    """
    if scan_dirs is None:
        scan_dirs = [
            "01_Planning",
            "02_Research_Projects",
            "03_Theoretical_Work",
            "memory",
        ]

    graph = KnowledgeGraph()

    for scan_dir in scan_dirs:
        root = vault_path / scan_dir
        if not root.exists():
            continue

        for md_file in root.rglob("*.md"):
            # Skip hidden dirs and node_modules-like paths
            parts = md_file.relative_to(vault_path).parts
            if any(p.startswith(".") for p in parts):
                continue

            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            rel_path = str(md_file.relative_to(vault_path))

            _extract_frontmatter_relations(content, rel_path, graph)
            _extract_claims(content, rel_path, graph)
            _extract_experiments(content, rel_path, graph)
            _extract_paper_ids(content, rel_path, graph)
            _extract_wikilinks(content, rel_path, graph)

    _log.info("KG built: %d entities, %d relations",
              len(graph.entities), len(graph.relations))
    return graph


def query_entity(graph: KnowledgeGraph, entity_id: str) -> dict:
    """Query all relations for a given entity."""
    return graph.query(entity_id)


def search_entities(graph: KnowledgeGraph, keyword: str) -> list[dict]:
    """Search entities by keyword."""
    return graph.search(keyword)


def save_graph(graph: KnowledgeGraph, output_path: Path) -> None:
    """Save graph to JSON file."""
    output_path.write_text(graph.to_json(), encoding="utf-8")
    _log.info("KG saved to %s", output_path)


def load_graph(input_path: Path) -> KnowledgeGraph:
    """Load graph from JSON file."""
    data = json.loads(input_path.read_text(encoding="utf-8"))
    graph = KnowledgeGraph()
    for eid, edata in data.get("entities", {}).items():
        graph.add_entity(Entity(**edata))
    for rdata in data.get("relations", []):
        graph.add_relation(Relation(**rdata))
    return graph


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

_TYPE_COLORS = {
    "claim": "#e74c3c",
    "experiment": "#3498db",
    "paper_ref": "#2ecc71",
    "concept": "#9b59b6",
    "model": "#f39c12",
    "synthesis": "#1abc9c",
    "evidence": "#e67e22",
    "reagent": "#95a5a6",
    "file": "#bdc3c7",
}

_REL_COLORS = {
    "supports": "#27ae60",
    "refutes": "#c0392b",
    "uses": "#2980b9",
    "cites": "#8e44ad",
    "links_to": "#95a5a6",
    "part_of": "#f39c12",
    "depends_on": "#e67e22",
    "blocks": "#e74c3c",
}


def visualize(
    graph: KnowledgeGraph,
    output_path: Path,
    *,
    max_link_nodes: int = 200,
) -> Path:
    """Generate an interactive HTML visualization of the knowledge graph.

    Uses pyvis to create a force-directed network graph.
    Nodes are colored by entity type, edges by relation type.
    If the graph has too many wikilink-only nodes (type='file' with
    only links_to relations), they are pruned to keep the view clean.

    Args:
        graph: Knowledge graph to visualize.
        output_path: Path for the output HTML file.
        max_link_nodes: Max number of generic link nodes to include.

    Returns:
        Path to the generated HTML file.
    """
    from pyvis.network import Network

    net = Network(
        height="900px", width="100%",
        bgcolor="#1a1a2e", font_color="white",
        directed=True, notebook=False,
    )
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=200)

    # Determine which entities are "important" (have type != file, or have
    # non-links_to relations)
    important_ids: set[str] = set()
    for e in graph.entities.values():
        if e.type != "file":
            important_ids.add(e.id)

    rel_entity_ids: set[str] = set()
    for r in graph.relations:
        if r.relation != "links_to":
            rel_entity_ids.add(r.source)
            rel_entity_ids.add(r.target)

    important_ids |= rel_entity_ids

    # Add important entity nodes
    added_nodes: set[str] = set()
    for eid in important_ids:
        e = graph.entities.get(eid)
        if e:
            color = _TYPE_COLORS.get(e.type, "#bdc3c7")
            size = 25 if e.type == "claim" else 18 if e.type == "experiment" else 15
            title = f"[{e.type}] {e.label}\n{e.source_file}"
            if e.metadata:
                title += f"\n{e.metadata}"
            net.add_node(eid, label=eid, color=color, size=size, title=title)
            added_nodes.add(eid)

    # Add wikilink target nodes that are referenced by important entities
    # (capped to avoid visual overload)
    link_targets: set[str] = set()
    for r in graph.relations:
        if r.source in added_nodes and r.target not in added_nodes:
            link_targets.add(r.target)
        if r.target in added_nodes and r.source not in added_nodes:
            link_targets.add(r.source)

    for lt in list(link_targets)[:max_link_nodes]:
        e = graph.entities.get(lt)
        if e:
            net.add_node(lt, label=lt, color="#555555", size=8,
                         title=f"[{e.type}] {e.label}")
        else:
            net.add_node(lt, label=lt, color="#555555", size=8,
                         title=lt)
        added_nodes.add(lt)

    # Add edges
    for r in graph.relations:
        if r.source in added_nodes and r.target in added_nodes:
            color = _REL_COLORS.get(r.relation, "#555555")
            width = 3 if r.relation in ("supports", "refutes", "uses") else 1
            net.add_edge(r.source, r.target, title=r.relation,
                         color=color, width=width)

    net.write_html(str(output_path), notebook=False)
    _log.info("KG visualization saved to %s", output_path)
    return output_path
