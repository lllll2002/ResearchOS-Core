"""
用 KMeans 强制将 227 篇论文分成 6 个主题，基于已有的 Qwen3 嵌入向量。
输出每个主题的关键词和论文列表。
"""
import json, pickle, sqlite3, sys
import numpy as np
from pathlib import Path

BASE = Path(r'E:\scholaraio\scholaraio-main\scholaraio-main')
DB = BASE / 'data' / 'index.db'
PAPERS_DIR = BASE / 'data' / 'papers'
OUT = BASE / 'data' / 'kmeans_topics.txt'
N_TOPICS = 6

# ── 1. 读取嵌入向量 ───────────────────────────────────────────────────────────
conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT paper_id, embedding FROM paper_vectors"
).fetchall()
conn.close()

paper_ids = [r[0] for r in rows]
vecs = np.array([np.frombuffer(r[1], dtype=np.float32) for r in rows])
print(f"Loaded {len(paper_ids)} vectors, dim={vecs.shape[1]}", file=sys.stderr)

# ── 2. 读取 meta ──────────────────────────────────────────────────────────────
id_to_meta = {}
for d in PAPERS_DIR.iterdir():
    mp = d / 'meta.json'
    if mp.exists():
        m = json.loads(mp.read_text(encoding='utf-8'))
        id_to_meta[m.get('id', '')] = m

# ── 3. KMeans 聚类 ───────────────────────────────────────────────────────────
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

vecs_norm = normalize(vecs)
km = KMeans(n_clusters=N_TOPICS, random_state=42, n_init=20, max_iter=500)
labels = km.fit_predict(vecs_norm)

# ── 4. 用 TF-IDF 提取每个主题的关键词 ────────────────────────────────────────
from sklearn.feature_extraction.text import TfidfVectorizer

docs = []
for pid in paper_ids:
    m = id_to_meta.get(pid, {})
    text = (m.get('title') or '') + ' ' + (m.get('abstract') or '')
    docs.append(text.lower())

tfidf = TfidfVectorizer(
    stop_words='english',
    ngram_range=(1, 2),
    max_features=5000,
    min_df=2,
)
tfidf_matrix = tfidf.fit_transform(docs)
vocab = np.array(tfidf.get_feature_names_out())

lines = [f'KMeans topic model: {N_TOPICS} topics, {len(paper_ids)} papers\n']

for t in range(N_TOPICS):
    idx = np.where(labels == t)[0]
    # cluster centroid tf-idf
    cluster_vecs = tfidf_matrix[idx].toarray()
    mean_vec = cluster_vecs.mean(axis=0)
    top_idx = mean_vec.argsort()[::-1][:10]
    keywords = ', '.join(vocab[top_idx])

    # paper list sorted by year
    papers_in_topic = []
    for i in idx:
        pid = paper_ids[i]
        m = id_to_meta.get(pid, {})
        papers_in_topic.append((m.get('year') or 0, m.get('first_author', '?'), m.get('title', '?'), m.get('journal', '?')))
    papers_in_topic.sort(key=lambda x: x[0])

    lines.append(f'{"="*65}')
    lines.append(f'Topic {t} ({len(idx)} papers): {keywords}')
    lines.append('='*65)
    for year, author, title, journal in papers_in_topic:
        lines.append(f'  [{year}] {author} | {title[:75]}')
        lines.append(f'         {journal[:60]}')
    lines.append('')

OUT.write_text('\n'.join(lines), encoding='utf-8')
print(f'Written to {OUT}')
