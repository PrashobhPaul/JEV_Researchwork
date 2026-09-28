"""Dense baseline: a small open embedding model on CPU. Cosine similarity over normalised vectors."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..corpus.github_issues import Record

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class DenseIndex:
    def __init__(self, ids: list[int], vectors: np.ndarray, model_name: str):
        self.ids, self.vectors, self.model_name = ids, vectors, model_name
        self._model = None

    @classmethod
    def build(cls, recs: list[Record], model_name: str = DEFAULT_MODEL, log=print) -> "DenseIndex":
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name, device="cpu")
        log(f"  embedding {len(recs)} records with {model_name}")
        vecs = model.encode([r.text for r in recs], batch_size=16, normalize_embeddings=True, show_progress_bar=False)
        idx = cls([r.id for r in recs], np.asarray(vecs, dtype=np.float32), model_name)
        idx._model = model
        return idx

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, ids=np.asarray(self.ids), vectors=self.vectors, model=np.asarray(self.model_name))

    @classmethod
    def load(cls, path: str | Path) -> "DenseIndex":
        z = np.load(path, allow_pickle=False)
        return cls(z["ids"].tolist(), z["vectors"], str(z["model"]))

    def _m(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def search(self, query: str, k: int = 50) -> list[tuple[int, float]]:
        q = self._m().encode([query], normalize_embeddings=True)[0]
        sims = self.vectors @ q
        top = np.argsort(-sims)[:k]
        return [(self.ids[i], float(sims[i])) for i in top]
