"""Content ingestion pipeline: read files, extract text/metadata, store in DB."""

import hashlib
import logging
import mimetypes
import os
import sqlite3
from pathlib import Path

import struct

from .db import vec_available
from .embeddings import chunk_text, generate_embedding
from .models import create_item, find_duplicate


def _serialize_f32(vec: list[float]) -> bytes:
    """Serialize a float list to raw bytes for sqlite-vec."""
    return struct.pack(f"{len(vec)}f", *vec)

logger = logging.getLogger(__name__)

# Map MIME type prefixes to item types
MIME_TYPE_MAP = {
    "text/markdown": "note",
    "text/plain": "note",
    "text/html": "document",
    "application/pdf": "document",
    "application/vnd.openxmlformats": "document",
    "application/msword": "document",
    "image/": "image",
    "text/calendar": "calendar",
    "text/vcard": "contact",
    "message/rfc822": "email",
}

# Extensions to type overrides
EXT_TYPE_MAP = {
    ".md": "note",
    ".txt": "note",
    ".py": "code_snippet",
    ".js": "code_snippet",
    ".ts": "code_snippet",
    ".rs": "code_snippet",
    ".go": "code_snippet",
    ".sh": "code_snippet",
    ".sql": "code_snippet",
    ".json": "file",
    ".yaml": "file",
    ".yml": "file",
    ".toml": "file",
    ".url": "bookmark",
    ".webloc": "bookmark",
    ".html": "document",
    ".htm": "document",
    ".pdf": "document",
    ".eml": "email",
    ".vcf": "contact",
    ".ics": "calendar",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".svg": "image",
}


def detect_type(file_path: Path) -> str:
    """Detect the item type from file extension and MIME type."""
    ext = file_path.suffix.lower()
    if ext in EXT_TYPE_MAP:
        return EXT_TYPE_MAP[ext]

    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        for prefix, item_type in MIME_TYPE_MAP.items():
            if mime.startswith(prefix):
                return item_type

    return "file"


def extract_text(file_path: Path) -> str | None:
    """Extract text content from a file. Returns None for unsupported formats."""
    ext = file_path.suffix.lower()

    # Plain text and code files
    text_exts = {
        ".md", ".txt", ".py", ".js", ".ts", ".rs", ".go", ".sh", ".sql",
        ".json", ".yaml", ".yml", ".toml", ".html", ".htm", ".css",
        ".csv", ".xml", ".ini", ".cfg", ".conf", ".log", ".eml", ".vcf",
        ".ics",
    }
    if ext in text_exts:
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

    # PDF
    if ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return "\n\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        except ImportError:
            logger.debug("pdfplumber not available for PDF extraction")
            return None
        except Exception as e:
            logger.warning(f"Failed to extract PDF {file_path}: {e}")
            return None

    # Word documents
    if ext in (".docx",):
        try:
            import docx
            doc = docx.Document(str(file_path))
            return "\n\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            logger.debug("python-docx not available")
            return None
        except Exception as e:
            logger.warning(f"Failed to extract docx {file_path}: {e}")
            return None

    return None


def extract_title(file_path: Path, content: str | None) -> str:
    """Derive a title from filename or content."""
    # Use filename without extension as default title
    title = file_path.stem.replace("_", " ").replace("-", " ").title()

    # For markdown, try to get the first heading
    if content and file_path.suffix.lower() == ".md":
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                break

    return title


def auto_tags(file_path: Path, item_type: str) -> list[str]:
    """Generate automatic tags based on file properties."""
    tags = [item_type]

    ext = file_path.suffix.lower()
    if ext:
        tags.append(ext.lstrip("."))

    return tags


def ingest_file(
    conn: sqlite3.Connection,
    file_path: str | Path,
    *,
    tags: list[str] | None = None,
    category_paths: list[str] | None = None,
    skip_duplicates: bool = True,
) -> int | None:
    """Ingest a single file into the knowledge base.

    Returns the item id, or None if skipped (duplicate/unsupported).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return None

    content = extract_text(file_path)
    if content is None:
        logger.info(f"Skipping unsupported format: {file_path}")
        return None

    # Check for duplicates
    if skip_duplicates and content:
        existing = find_duplicate(conn, content)
        if existing:
            logger.info(f"Duplicate found (item {existing}): {file_path}")
            return None

    item_type = detect_type(file_path)
    title = extract_title(file_path, content)
    file_tags = auto_tags(file_path, item_type)
    if tags:
        file_tags.extend(tags)

    stat = file_path.stat()
    metadata = {
        "original_filename": file_path.name,
        "file_size": stat.st_size,
        "extension": file_path.suffix.lower(),
    }

    item_id = create_item(
        conn,
        type=item_type,
        title=title,
        content=content,
        source_path=str(file_path.resolve()),
        metadata=metadata,
        tags=file_tags,
        category_paths=category_paths,
    )

    # Generate and store embedding
    if vec_available() and content:
        _store_embedding(conn, item_id, content)

    logger.info(f"Ingested {file_path.name} as {item_type} (id={item_id})")
    return item_id


def _store_embedding(
    conn: sqlite3.Connection, item_id: int, content: str
) -> None:
    """Generate embedding for content and store in vec table."""
    # For long content, embed just the first chunk (title + beginning)
    chunks = chunk_text(content)
    embedding = generate_embedding(chunks[0])
    if embedding is None:
        return

    try:
        conn.execute(
            "INSERT INTO items_vec (item_id, embedding) VALUES (?, ?)",
            (item_id, _serialize_f32(embedding)),
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to store embedding for item {item_id}: {e}")


def ingest_directory(
    conn: sqlite3.Connection,
    directory: str | Path,
    *,
    tags: list[str] | None = None,
    category_paths: list[str] | None = None,
    recursive: bool = False,
) -> list[int]:
    """Ingest all supported files in a directory.

    Returns list of created item ids.
    """
    directory = Path(directory)
    if not directory.is_dir():
        logger.warning(f"Not a directory: {directory}")
        return []

    ids = []
    pattern = "**/*" if recursive else "*"

    for path in sorted(directory.glob(pattern)):
        if path.is_file() and not path.name.startswith("."):
            item_id = ingest_file(
                conn, path, tags=tags, category_paths=category_paths
            )
            if item_id is not None:
                ids.append(item_id)

    return ids
