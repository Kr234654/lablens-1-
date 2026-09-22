"""
Retrieval for the app's RAG (retrieval-augmented generation) feature.

- knowledge_base.py holds a small set of hand-written health-education articles.
- On startup, each article is split into overlapping chunks and turned into a vector.
- A question is turned into a vector the same way, and we return the chunks whose vectors
  are closest to it (cosine similarity) — this is the "retrieval" step.
- explain.py then either (a) hands the retrieved chunks to the LLM as grounding context
  ("augmented generation"), or (b) returns the best chunk directly when there is no LLM key,
  so retrieval is useful and testable even in basic mode.

Two ways to turn text into a vector are supported:
  - TF-IDF + cosine similarity, computed with plain Python (no extra dependencies, no network
    call, so it always works and is fast to test).
  - Real embeddings from an OpenAI-compatible API, used automatically when an OpenAI key is
    configured (Groq's API does not currently serve embeddings, so this path is OpenAI-only).
Both return the same shape of result, so the rest of the app does not need to know which one ran.
"""
import math
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional

from knowledge_base import ARTICLES

CHUNK_WORDS = 90
CHUNK_OVERLAP = 20
STOPWORDS = set(
    "a an the is are was were be been being of to in on for with and or but if then so as at by "
    "from this that these those it its it's your you my i we they he she them his her our their "
    "not no can could should would will just about into over under more most very also than "
    "do does did have has had what when where which who how why "
    "tell told telling say says said ask asked asking make made making using used use need needs "
    "needed want wants wanted know known knows look looks looking come comes going go goes take "
    "takes taken give gives given get gets getting please help me thanks thank".split()
)
WORD_RE = re.compile(r"[a-z][a-z\-]+")


@dataclass
class Chunk:
    article_id: str
    title: str
    text: str
    tokens: Counter = field(default_factory=Counter)
    vector: Optional[list] = None  # only set when using real embeddings


def _tokenize(text: str) -> List[str]:
    return [w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS and len(w) > 2]


def _make_chunks() -> List[Chunk]:
    chunks = []
    for article in ARTICLES:
        words = article["text"].split()
        step = CHUNK_WORDS - CHUNK_OVERLAP
        starts = range(0, max(len(words), 1), step) if len(words) > CHUNK_WORDS else [0]
        for start in starts:
            piece = " ".join(words[start:start + CHUNK_WORDS])
            if piece:
                chunks.append(Chunk(article_id=article["id"], title=article["title"], text=piece))
        if not any(c.article_id == article["id"] for c in chunks):  # very short article: keep it whole
            chunks.append(Chunk(article_id=article["id"], title=article["title"], text=article["text"]))
    return chunks


# ---------------------------------------------------------------- TF-IDF backend (default, offline)
def _build_tfidf(chunks: List[Chunk]) -> dict:
    doc_freq = Counter()
    for c in chunks:
        c.tokens = Counter(_tokenize(c.text))
        doc_freq.update(c.tokens.keys())
    n_docs = len(chunks) or 1
    idf = {term: math.log((n_docs + 1) / (df + 1)) + 1 for term, df in doc_freq.items()}
    return idf


def _tfidf_vector(tokens: Counter, idf: dict) -> dict:
    total = sum(tokens.values()) or 1
    return {term: (count / total) * idf.get(term, 0.0) for term, count in tokens.items()}


def _cosine(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    common = a.keys() & b.keys()
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


# ---------------------------------------------------------------- optional real-embeddings backend
_EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def _embeddings_client():
    """Only OpenAI serves embeddings for the model above, so we use them only when there is no
    custom base_url (i.e. not when the key is for Groq or another OpenAI-compatible provider)."""
    key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key or os.getenv("LLM_BASE_URL"):
        return None
    from openai import OpenAI

    return OpenAI(api_key=key, timeout=20, max_retries=1)


def _embed_many(client, texts: List[str]) -> Optional[List[list]]:
    try:
        res = client.embeddings.create(model=_EMBED_MODEL, input=texts)
        return [d.embedding for d in res.data]
    except Exception:
        return None


def _dot(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: list) -> float:
    return math.sqrt(sum(x * x for x in a)) or 1.0


# ---------------------------------------------------------------- index
class Index:
    def __init__(self):
        self.chunks = _make_chunks()
        self.idf = _build_tfidf(self.chunks)
        self.backend = "tfidf"

        client = _embeddings_client()
        if client is not None:
            vectors = _embed_many(client, [c.text for c in self.chunks])
            if vectors:
                for chunk, vec in zip(self.chunks, vectors):
                    chunk.vector = vec
                self.backend = "embeddings"
        self._client = client if self.backend == "embeddings" else None

    def search(self, query: str, k: int = 3, min_score: float = 0.08) -> List[dict]:
        if not query.strip():
            return []

        if self.backend == "embeddings":
            q_vec = _embed_many(self._client, [query])
            if q_vec:
                q = q_vec[0]
                scored = [(_dot(q, c.vector) / (_norm(q) * _norm(c.vector)), c) for c in self.chunks]
            else:  # the embedding call failed just for this query: fall back to TF-IDF for it
                scored = self._tfidf_scores(query)
        else:
            scored = self._tfidf_scores(query)

        scored.sort(key=lambda pair: pair[0], reverse=True)
        results, seen_articles = [], set()
        for score, chunk in scored:
            if score < min_score or chunk.article_id in seen_articles:
                continue
            results.append({"article_id": chunk.article_id, "title": chunk.title, "text": chunk.text, "score": round(score, 3)})
            seen_articles.add(chunk.article_id)
            if len(results) >= k:
                break
        return results

    def _tfidf_scores(self, query: str):
        q_vec = _tfidf_vector(Counter(_tokenize(query)), self.idf)
        return [(_cosine(q_vec, _tfidf_vector(c.tokens, self.idf)), c) for c in self.chunks]


_index: Optional[Index] = None


def get_index() -> Index:
    """Built once and cached: chunking and (if used) calling the embeddings API happen only at first use."""
    global _index
    if _index is None:
        _index = Index()
    return _index


def retrieve(query: str, k: int = 3) -> List[dict]:
    return get_index().search(query, k=k)
