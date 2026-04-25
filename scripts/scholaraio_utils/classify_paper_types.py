"""
按论文类型分类所有论文：Research / Review / Conference / Preprint / Comment 等。
分类依据：
1. meta.json 已有 paper_type 字段
2. 期刊/会议名称关键词
3. 标题关键词（review, survey, overview, perspective, commentary 等）
4. 摘要开头句式
输出到 data/paper_types.txt
"""
import json, re
from pathlib import Path
from collections import defaultdict

papers_dir = Path(r'E:\scholaraio\scholaraio-main\scholaraio-main\data\papers')
out_path = Path(r'E:\scholaraio\scholaraio-main\scholaraio-main\data\paper_types.txt')

# 关键词规则（全部小写匹配）
REVIEW_TITLE_KW = [
    'review', 'survey', 'overview', 'perspective', 'perspectives',
    'state of the art', 'state-of-the-art', 'tutorial', 'progress',
    'advances', 'recent advances', 'current status', 'emerging',
    'landscape', 'roadmap', 'challenges and', 'opportunities',
]
COMMENT_TITLE_KW = [
    'commentary', 'editorial',
    'erratum', 'corrigendum',
]
COMMENT_TITLE_EXACT = [
    # Only match "correction" when it's the standalone correction/retraction type
    r'^correction\b', r'^corrigendum\b', r'^erratum\b',
]
PREPRINT_JOURNAL_KW = [
    'arxiv', 'biorxiv', 'medrxiv', 'chemrxiv', 'preprint',
]
CONFERENCE_JOURNAL_KW = [
    'conference', 'symposium', 'workshop', 'congress',
    'international conference', 'annual meeting',
    'conf.', 'isit', 'iscas', 'embc',
]
# Journals with "proceedings" in the name that are actually journals, not conferences
JOURNAL_NOT_CONFERENCE = [
    'proceedings of the national academy',
    'proceedings of the royal society',
    'proceedings of the ieee',  # the journal, not a conference
]

def classify(m):
    # 1. 已有 paper_type 字段（thesis 等）
    pt = (m.get('paper_type') or '').lower()
    if pt == 'thesis':
        return 'Thesis'

    title = (m.get('title') or '').lower()
    journal = (m.get('journal') or '').lower()
    abstract = (m.get('abstract') or '').lower()[:300]

    # 2. Preprint
    for kw in PREPRINT_JOURNAL_KW:
        if kw in journal:
            return 'Preprint'

    # 3. Conference paper (exclude known journal "proceedings")
    is_journal_proceedings = any(kw in journal for kw in JOURNAL_NOT_CONFERENCE)
    if not is_journal_proceedings:
        for kw in CONFERENCE_JOURNAL_KW:
            if kw in journal:
                return 'Conference'

    # 4. Comment / Editorial
    for kw in COMMENT_TITLE_KW:
        if kw in title:
            return 'Comment/Editorial'
    for pattern in COMMENT_TITLE_EXACT:
        if re.match(pattern, title):
            return 'Comment/Editorial'

    # 5. Review / Survey
    for kw in REVIEW_TITLE_KW:
        if kw in title:
            return 'Review/Survey'

    # 6. Abstract hints
    review_abstract_hints = [
        'in this review', 'we review', 'this review', 'herein, we review',
        'this survey', 'we survey', 'in this survey',
        'we provide an overview', 'we summarize', 'we highlight',
    ]
    for hint in review_abstract_hints:
        if hint in abstract:
            return 'Review/Survey'

    return 'Research Article'

papers = []
for d in papers_dir.iterdir():
    mp = d / 'meta.json'
    if not mp.exists():
        continue
    m = json.loads(mp.read_text(encoding='utf-8'))
    ptype = classify(m)
    papers.append({
        'type': ptype,
        'year': m.get('year') or 0,
        'author': m.get('first_author', '?'),
        'title': m.get('title', '?'),
        'journal': m.get('journal', '?'),
        'dir': d.name,
    })

# 按类型分组
grouped = defaultdict(list)
for p in papers:
    grouped[p['type']].append(p)

# 输出
lines = [f'Paper type classification: {len(papers)} papers\n']
type_order = ['Research Article', 'Review/Survey', 'Conference', 'Preprint', 'Comment/Editorial', 'Thesis']
for ptype in type_order:
    grp = sorted(grouped.get(ptype, []), key=lambda x: x['year'] or 0)
    if not grp:
        continue
    lines.append(f'{"="*65}')
    lines.append(f'{ptype} ({len(grp)} papers)')
    lines.append('='*65)
    for p in grp:
        lines.append(f"  [{p['year']}] {p['author']} | {p['title'][:75]}")
        lines.append(f"         {p['journal'][:60]}")
    lines.append('')

# summary
lines.append('--- Summary ---')
for ptype in type_order:
    grp = grouped.get(ptype, [])
    if grp:
        lines.append(f'  {ptype}: {len(grp)}')

out_path.write_text('\n'.join(lines), encoding='utf-8')
print(f'Written {len(papers)} papers to {out_path}')
