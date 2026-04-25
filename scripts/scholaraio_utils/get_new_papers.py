"""获取新入库论文列表（199篇中按年份+标题列出，标注topic）"""
import os, json, pickle

papers_dir = r'E:\scholaraio\scholaraio-main\scholaraio-main\data\papers'
topic_model_dir = r'E:\scholaraio\scholaraio-main\scholaraio-main\data\topic_model'
out_path = r'E:\scholaraio\scholaraio-main\scholaraio-main\data\new_papers_list.txt'

with open(os.path.join(topic_model_dir, 'scholaraio_meta.pkl'), 'rb') as f:
    meta = pickle.load(f)

id_topic = dict(zip(meta['paper_ids'], meta['topics']))

papers = []
for d in os.listdir(papers_dir):
    mpath = os.path.join(papers_dir, d, 'meta.json')
    if not os.path.exists(mpath):
        continue
    with open(mpath, encoding='utf-8') as f:
        m = json.load(f)
    papers.append({
        'topic': id_topic.get(m.get('id',''), -99),
        'year': m.get('year') or 0,
        'title': m.get('title','?'),
        'first_author': m.get('first_author','?'),
        'journal': m.get('journal','?'),
        'abstract': (m.get('abstract') or '')[:250].replace('\n',' '),
        'dir': d,
    })

papers.sort(key=lambda x: (x['topic'], x['year'] or 0))

lines = [f'Total: {len(papers)} papers, 2 topics\n']
for t in [0, 1]:
    group = [p for p in papers if p['topic'] == t]
    kw = 'DNA Computing / Logic / Biocomputing / Synthetic Biology' if t == 0 else 'DNA Data Storage / Coding / AI-enhanced'
    lines.append(f'\n{"="*60}')
    lines.append(f'Topic {t} ({len(group)} papers): {kw}')
    lines.append('='*60)
    for p in group:
        lines.append(f"[{p['year']}] {p['first_author']} | {p['title'][:85]}")
        lines.append(f"  {p['journal'][:70]}")
        lines.append(f"  {p['abstract'][:200]}")
        lines.append('')

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'Written: {len(papers)} papers to {out_path}')
