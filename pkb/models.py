"""Item CRUD operations with tag and category management."""

import hashlib
import json
import sqlite3
from datetime import datetime


def _content_hash(content: str) -> str:
    """SHA-256 hash of content for deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _word_count(text: str | None) -> int:
    if not text:
        return 0
    return len(text.split())


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

def create_item(
    conn: sqlite3.Connection,
    *,
    type: str,
    title: str | None = None,
    content: str | None = None,
    summary: str | None = None,
    source_path: str | None = None,
    metadata: dict | None = None,
    tags: list[str] | None = None,
    category_paths: list[str] | None = None,
) -> int:
    """Insert a new item and return its id."""
    ch = _content_hash(content) if content else None
    wc = _word_count(content)
    meta_json = json.dumps(metadata) if metadata else None

    cur = conn.execute(
        """INSERT INTO items (type, title, content, summary, source_path,
                              content_hash, word_count, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (type, title, content, summary, source_path, ch, wc, meta_json),
    )
    item_id = cur.lastrowid

    if tags:
        for tag_name in tags:
            add_tag(conn, item_id, tag_name)

    if category_paths:
        for path in category_paths:
            assign_category(conn, item_id, path)

    conn.commit()
    return item_id


def get_item(conn: sqlite3.Connection, item_id: int) -> dict | None:
    """Fetch a single item by id, including its tags and categories."""
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return None

    item = dict(row)
    item["tags"] = get_item_tags(conn, item_id)
    item["categories"] = get_item_categories(conn, item_id)
    return item


def update_item(
    conn: sqlite3.Connection,
    item_id: int,
    **fields,
) -> bool:
    """Update an item's fields. Returns True if the row was found."""
    if not fields:
        return False

    allowed = {
        "type", "title", "content", "summary", "source_path",
        "content_hash", "word_count", "metadata", "updated_at",
    }
    bad_keys = set(fields) - allowed
    if bad_keys:
        raise ValueError(f"Invalid column(s): {bad_keys}")

    # Recalculate derived fields if content changed
    if "content" in fields:
        fields["content_hash"] = _content_hash(fields["content"])
        fields["word_count"] = _word_count(fields["content"])

    fields["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")

    if "metadata" in fields and isinstance(fields["metadata"], dict):
        fields["metadata"] = json.dumps(fields["metadata"])

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [item_id]

    cur = conn.execute(
        f"UPDATE items SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    return cur.rowcount > 0


def delete_item(conn: sqlite3.Connection, item_id: int) -> bool:
    """Delete an item and its tag/category associations (via CASCADE)."""
    cur = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    return cur.rowcount > 0


def list_items(
    conn: sqlite3.Connection,
    *,
    type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List items with optional type filter."""
    query = "SELECT * FROM items"
    params: list = []

    if type:
        query += " WHERE type = ?"
        params.append(type)

    query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def find_duplicate(conn: sqlite3.Connection, content: str) -> int | None:
    """Return item id if content with this hash already exists."""
    ch = _content_hash(content)
    row = conn.execute(
        "SELECT id FROM items WHERE content_hash = ?", (ch,)
    ).fetchone()
    return row["id"] if row else None


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def get_or_create_tag(conn: sqlite3.Connection, name: str) -> int:
    """Return tag id, creating the tag if it doesn't exist."""
    row = conn.execute(
        "SELECT id FROM tags WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
    return cur.lastrowid


def add_tag(conn: sqlite3.Connection, item_id: int, tag_name: str) -> None:
    """Tag an item, creating the tag if needed."""
    tag_id = get_or_create_tag(conn, tag_name)
    conn.execute(
        "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
        (item_id, tag_id),
    )


def remove_tag(conn: sqlite3.Connection, item_id: int, tag_name: str) -> None:
    """Remove a tag from an item."""
    conn.execute(
        """DELETE FROM item_tags WHERE item_id = ? AND tag_id = (
               SELECT id FROM tags WHERE name = ? COLLATE NOCASE
           )""",
        (item_id, tag_name),
    )
    conn.commit()


def get_item_tags(conn: sqlite3.Connection, item_id: int) -> list[str]:
    rows = conn.execute(
        """SELECT t.name FROM tags t
           JOIN item_tags it ON it.tag_id = t.id
           WHERE it.item_id = ?
           ORDER BY t.name""",
        (item_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def list_tags(conn: sqlite3.Connection) -> list[dict]:
    """List all tags with item counts."""
    rows = conn.execute(
        """SELECT t.id, t.name, COUNT(it.item_id) as count
           FROM tags t LEFT JOIN item_tags it ON it.tag_id = t.id
           GROUP BY t.id ORDER BY t.name"""
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def get_or_create_category(conn: sqlite3.Connection, path: str) -> int:
    """Ensure the full category path exists, creating intermediaries as needed.

    Path format: '/work/projects/alpha'
    """
    path = path.strip("/")
    parts = path.split("/")

    parent_id = None
    built = ""
    cat_id = None

    for part in parts:
        built += f"/{part}"
        row = conn.execute(
            "SELECT id FROM categories WHERE path = ?", (built,)
        ).fetchone()
        if row:
            cat_id = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO categories (name, path, parent_id) VALUES (?, ?, ?)",
                (part, built, parent_id),
            )
            cat_id = cur.lastrowid
        parent_id = cat_id

    return cat_id


def assign_category(
    conn: sqlite3.Connection, item_id: int, category_path: str
) -> None:
    """Assign an item to a category, creating the path if needed."""
    cat_id = get_or_create_category(conn, category_path)
    conn.execute(
        "INSERT OR IGNORE INTO item_categories (item_id, category_id) VALUES (?, ?)",
        (item_id, cat_id),
    )


def get_item_categories(conn: sqlite3.Connection, item_id: int) -> list[str]:
    rows = conn.execute(
        """SELECT c.path FROM categories c
           JOIN item_categories ic ON ic.category_id = c.id
           WHERE ic.item_id = ?
           ORDER BY c.path""",
        (item_id,),
    ).fetchall()
    return [r["path"] for r in rows]


def list_categories(conn: sqlite3.Connection) -> list[dict]:
    """List all categories with item counts."""
    rows = conn.execute(
        """SELECT c.id, c.name, c.path, c.parent_id,
                  COUNT(ic.item_id) as count
           FROM categories c
           LEFT JOIN item_categories ic ON ic.category_id = c.id
           GROUP BY c.id ORDER BY c.path"""
    ).fetchall()
    return [dict(r) for r in rows]
