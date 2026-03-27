"""Embedding generation with graceful degradation.

Priority: local sentence-transformers -> OpenAI API -> None (FTS5-only mode).
"""

import logging
import os

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
_model = None
_UNINITIALIZED = object()
_backend = _UNINITIALIZED  # 'local', 'openai', or None after init


def _try_local():
    """Try loading local sentence-transformers model."""
    global _model, _backend
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _backend = "local"
        logger.info("Using local sentence-transformers for embeddings")
        return True
    except ImportError:
        logger.debug("sentence-transformers not available")
        return False


def _try_openai():
    """Try using OpenAI embeddings API."""
    global _backend
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.debug("OPENAI_API_KEY not set")
        return False
    try:
        import openai  # noqa: F401
        _backend = "openai"
        logger.info("Using OpenAI API for embeddings")
        return True
    except ImportError:
        logger.debug("openai package not available")
        return False


def init_embeddings() -> str | None:
    """Initialize embedding backend. Returns backend name or None."""
    global _backend
    if _backend is not _UNINITIALIZED:
        return _backend

    if _try_local():
        return _backend
    if _try_openai():
        return _backend

    logger.warning(
        "No embedding backend available — running in FTS5-only mode"
    )
    _backend = None
    return None


def get_backend() -> str | None:
    """Return the current backend name."""
    return _backend


def generate_embedding(text: str) -> list[float] | None:
    """Generate an embedding vector for the given text.

    Returns a list of floats (384-dim for local, projected for OpenAI)
    or None if no backend is available.
    """
    if _backend is _UNINITIALIZED:
        init_embeddings()

    if _backend == "local":
        vec = _model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    if _backend == "openai":
        import openai
        client = openai.OpenAI()
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=EMBEDDING_DIM,
        )
        return resp.data[0].embedding

    return None


def generate_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Generate embeddings for a batch of texts."""
    if _backend is _UNINITIALIZED:
        init_embeddings()

    if _backend == "local":
        vecs = _model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    if _backend == "openai":
        import openai
        client = openai.OpenAI()
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
            dimensions=EMBEDDING_DIM,
        )
        # OpenAI returns in order of input
        return [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]

    return [None] * len(texts)


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start = end - overlap

    return chunks
