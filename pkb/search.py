"""Hybrid search: FTS5 keyword search + sqlite-vec semantic search with RRF."""

import sqlite3
import struct

from .db import vec_available
from .embeddings import generate_embedding


def _serialize_f32(vec: list[float]) -> bytes:
    """Serialize a float list to raw bytes for sqlite-vec."""
    return struct.pack(f"{len(vec)}f", *vec)


def fts5_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    type_filter: str | None = None,
) -> list[dict]:
    """Full-text keyword search using FTS5 with BM25 ranking."""
    where_clause = ""
    params: list = [query, limit]

    if type_filter:
        where_clause = "AND i.type = ?"
        params = [query, type_filter, limit]

    rows = conn.execute(
        f"""SELECT i.*, rank as score
            FROM items_fts fts
            JOIN items i ON i.id = fts.rowid
            WHERE items_fts MATCH ?
            {where_clause}
            ORDER BY rank
            LIMIT ?""",
        params,
    ).fetchall()

    return [dict(r) for r in rows]


def vector_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
) -> list[dict]:
    """Semantic search using sqlite-vec. Returns empty list if vec unavailable."""
    if not vec_available():
        return []

    embedding = generate_embedding(query)
    if embedding is None:
        return []

    query_bytes = _serialize_f32(embedding)

    rows = conn.execute(
        """SELECT v.item_id, v.distance as score
           FROM items_vec v
           WHERE embedding MATCH ? AND k = ?
           ORDER BY distance""",
        (query_bytes, limit),
    ).fetchall()

    # Fetch full items
    results = []
    for r in rows:
        item_row = conn.execute(
            "SELECT * FROM items WHERE id = ?", (r["item_id"],)
        ).fetchone()
        if item_row:
            item = dict(item_row)
            item["vec_score"] = r["score"]
            results.append(item)

    return results


def hybrid_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    type_filter: str | None = None,
    k: int = 60,
) -> list[dict]:
    """Hybrid search combining FTS5 and sqlite-vec via Reciprocal Rank Fusion.

    RRF formula: score(d) = sum( 1 / (k + rank_i) ) for each ranking system.
    k=60 is the standard constant from the original RRF paper.
    """
    fts_results = fts5_search(conn, query, limit=limit * 2, type_filter=type_filter)
    vec_results = vector_search(conn, query, limit=limit * 2)

    # Build RRF scores
    rrf_scores: dict[int, float] = {}
    item_data: dict[int, dict] = {}

    for rank, item in enumerate(fts_results):
        item_id = item["id"]
        rrf_scores[item_id] = rrf_scores.get(item_id, 0) + 1.0 / (k + rank + 1)
        item_data[item_id] = item

    for rank, item in enumerate(vec_results):
        item_id = item["id"]
        rrf_scores[item_id] = rrf_scores.get(item_id, 0) + 1.0 / (k + rank + 1)
        if item_id not in item_data:
            item_data[item_id] = item

    # Sort by RRF score descending
    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

    results = []
    for item_id in sorted_ids[:limit]:
        item = item_data[item_id]
        item["rrf_score"] = rrf_scores[item_id]
        results.append(item)

    return results


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    type_filter: str | None = None,
    tags: list[str] | None = None,
    category_path: str | None = None,
) -> list[dict]:
    """High-level search with optional tag and category filters.

    Uses hybrid search when vec is available, falls back to FTS5-only.
    """
    if vec_available():
        results = hybrid_search(
            conn, query, limit=limit * 2, type_filter=type_filter
        )
    else:
        results = fts5_search(
            conn, query, limit=limit * 2, type_filter=type_filter
        )

    # Post-filter by tags
    if tags:
        tag_set = {t.lower() for t in tags}
        filtered = []
        for item in results:
            item_tags = conn.execute(
                """SELECT t.name FROM tags t
                   JOIN item_tags it ON it.tag_id = t.id
                   WHERE it.item_id = ?""",
                (item["id"],),
            ).fetchall()
            item_tag_names = {r["name"].lower() for r in item_tags}
            if tag_set & item_tag_names:
                filtered.append(item)
        results = filtered

    # Post-filter by category
    if category_path:
        filtered = []
        for item in results:
            cats = conn.execute(
                """SELECT c.path FROM categories c
                   JOIN item_categories ic ON ic.category_id = c.id
                   WHERE ic.item_id = ? AND c.path LIKE ?""",
                (item["id"], category_path + "%"),
            ).fetchall()
            if cats:
                filtered.append(item)
        results = filtered

    return results[:limit]
