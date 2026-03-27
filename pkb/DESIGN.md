# PKB Design Notes

## Schema Decisions

### Shared Base Table (`items`)
All content types share a single `items` table with common fields (title, content, type, timestamps). Type-specific metadata goes in the JSON `metadata` column via SQLite's JSON1 extension. This gives us a unified query interface — every search, tag, and category operation works across all content types without type-specific SQL.

I considered separate type-extension tables (e.g., `item_email`, `item_bookmark`) but deferred them. The JSON metadata column handles type-specific fields well enough for v1, and adding extension tables later is a non-breaking migration.

### FTS5 External Content Table
The `items_fts` table uses FTS5's external content mode (`content='items'`), which avoids duplicating text storage. Triggers keep FTS5 in sync on insert/update/delete. The `porter unicode61` tokenizer gives us stemming and Unicode normalization out of the box.

### sqlite-vec for Semantic Search
The `items_vec` virtual table stores 384-dimensional embeddings matching the `all-MiniLM-L6-v2` model. sqlite-vec is optional — if the extension isn't installed, the system falls back to FTS5-only search with no errors.

### Hybrid Search with RRF
When both FTS5 and sqlite-vec are available, search results are merged using Reciprocal Rank Fusion (k=60). RRF is simple, parameter-light, and well-studied — it reliably outperforms either ranking alone because keyword matches and semantic matches catch different things.

### Tags vs Categories
Tags are flat, many-to-many (junction table). Categories are hierarchical using materialized paths (e.g., `/work/projects/alpha`), which are simple to query with LIKE and intuitive to display. Both can be combined in compound filters.

### Deduplication
Content is SHA-256 hashed on insert. The `find_duplicate` check prevents re-ingesting identical files.

## Graceful Degradation

The system works at three capability levels:
1. **Full** — FTS5 + sqlite-vec + embeddings (local or API)
2. **Partial** — FTS5 + embeddings in items_vec (if sqlite-vec available but embedding backend limited)
3. **Minimal** — FTS5 only (no sqlite-vec, no embedding backend)

Each level is fully functional; you just get progressively better search quality with more capabilities available.

## File Layout

```
pkb/
├── __init__.py       # Package metadata
├── schema.sql        # DDL for all tables, triggers, indexes
├── db.py             # Connection management, init, migrations
├── models.py         # Item CRUD, tags, categories
├── search.py         # FTS5, vector, hybrid search with RRF
├── embeddings.py     # Embedding generation (local/OpenAI/none)
├── ingest.py         # File ingestion pipeline
├── cli.py            # Click CLI interface
├── requirements.txt  # Dependencies
└── DESIGN.md         # This file
```
