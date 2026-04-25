"""读取所有论文的 meta.json，按 topic 分组，写入 data/topics_output.txt"""
import os, json, sys, pickle

papers_dir = r'E:\scholaraio\scholaraio-main\scholaraio-main\data\papers'
topic_model_dir = r'E:\scholaraio\scholaraio-main\scholaraio-main\data\topic_model'
out_path = r'E:\scholaraio\scholaraio-main\scholaraio-main\data\topics_output.txt'

# Load topic assignments
with open(os.path.join(topic_model_dir, 'scholaraio_meta.pkl'), 'rb') as f:
    meta = pickle.load(f)

paper_ids = meta['paper_ids']
topics = meta['topics']
id_topic = dict(zip(paper_ids, topics))

# Load all paper meta.json
papers = []
for d in os.listdir(papers_dir):
    meta_path = os.path.join(papers_dir, d, 'meta.json')
    if os.path.exists(meta_path):
        with open(meta_path, encoding='utf-8') as f:
            m = json.load(f)
        pid = m.get('id', '')
        topic = id_topic.get(pid, -99)
        papers.append({
            'topic': topic,
            'year': m.get('year') or '?',
            'title': m.get('title', '?'),
            'first_author': m.get('first_author', '?'),
            'journal': m.get('journal', '?'),
            'abstract': (m.get('abstract') or '').replace('\n', ' ')[:300],
            'dir': d
        })

papers.sort(key=lambda x: (x['topic'], str(x['year'])))

lines = []
for t in sorted(set(p['topic'] for p in papers)):
    label = f"Topic {t}" if t >= 0 else "Outlier"
    group = [p for p in papers if p['topic'] == t]
    lines.append(f"\n{'='*60}")
    lines.append(f"{label} ({len(group)} papers)")
    lines.append('='*60)
    for p in group:
        lines.append(f"[{p['year']}] {p['first_author']} | {p['title'][:90]}")
        lines.append(f"  Journal: {p['journal']}")
        lines.append(f"  Abstract: {p['abstract']}")
        lines.append("")

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"Written to {out_path}, {len(papers)} papers")
