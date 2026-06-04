import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False
    logger.warning("sentence-transformers not installed — embedding scoring disabled")


def cosine_similarity(a, b) -> float:
    import numpy as np
    a, b = np.array(a), np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def embed_text(text: str) -> Optional[list[float]]:
    if not _AVAILABLE or not text:
        return None
    return _MODEL.encode(text, normalize_embeddings=True).tolist()


def similarity(text_a: str, text_b: str) -> Optional[float]:
    if not _AVAILABLE:
        return None
    vec_a = embed_text(text_a)
    vec_b = embed_text(text_b)
    if vec_a is None or vec_b is None:
        return None
    return cosine_similarity(vec_a, vec_b)
