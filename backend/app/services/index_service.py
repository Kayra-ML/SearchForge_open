"""
SQLite + FTS5 index service.

Schema:
    documents   — one row per Drive file (metadata)
    pages       — one row per PDF page (compressed text)
    pages_fts   — FTS5 contentless index pointing at pages

Türkçe normalization is applied at both index and query time.
"""

import logging
import sqlite3
import time
import zlib
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

_DB_PATH: Optional[Path] = None
_SIZE_WARNING_BYTES = 1.5 * 1024 ** 3  # 1.5 GB


def get_db_path() -> Path:
    global _DB_PATH
    if _DB_PATH is None:
        base = Path(__file__).resolve().parent.parent.parent / "data"
        base.mkdir(parents=True, exist_ok=True)
        _DB_PATH = base / "search_index.db"
    return _DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    drive_file_id   TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    mime_type       TEXT    NOT NULL DEFAULT 'application/pdf',
    drive_path      TEXT    NOT NULL DEFAULT '',
    size            INTEGER,
    modified_time   TEXT,
    indexed_at      TEXT,
    page_count      INTEGER DEFAULT 0,
    index_status    TEXT    NOT NULL DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_documents_drive_file_id ON documents(drive_file_id);
CREATE INDEX IF NOT EXISTS idx_documents_name ON documents(name);

CREATE TABLE IF NOT EXISTS pages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number     INTEGER NOT NULL,
    compressed_text BLOB
);

CREATE INDEX IF NOT EXISTS idx_pages_document_id ON pages(document_id);

CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
    body,
    content='',
    tokenize='unicode61'
);

CREATE TABLE IF NOT EXISTS sync_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    files_total INTEGER DEFAULT 0,
    files_indexed INTEGER DEFAULT 0,
    files_skipped INTEGER DEFAULT 0,
    files_failed  INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'running'
);
"""


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(DDL)
        conn.commit()
        logger.info("SQLite index DB initialized at %s", get_db_path())
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Turkish normalization
# ---------------------------------------------------------------------------

def normalize_tr(text: str) -> str:
    """
    Lowercase with Turkish-aware I/İ/ı handling.
    Does NOT strip ç/ş/ğ/ö/ü — keeps them intact so search is precise.
    """
    # Turkish-specific casing
    text = text.replace("İ", "i").replace("I", "ı")
    return text.casefold()


# ---------------------------------------------------------------------------
# Index write operations
# ---------------------------------------------------------------------------

def compress(text: str) -> bytes:
    return zlib.compress(text.encode("utf-8"), level=6)


def decompress(blob: bytes) -> str:
    return zlib.decompress(blob).decode("utf-8")


def upsert_document(
    conn: sqlite3.Connection,
    drive_file_id: str,
    name: str,
    mime_type: str,
    drive_path: str,
    size: Optional[int],
    modified_time: Optional[str],
) -> int:
    """Insert or update document record. Returns document id."""
    conn.execute(
        """
        INSERT INTO documents (drive_file_id, name, mime_type, drive_path, size, modified_time, index_status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ON CONFLICT(drive_file_id) DO UPDATE SET
            name          = excluded.name,
            drive_path    = excluded.drive_path,
            size          = excluded.size,
            modified_time = excluded.modified_time,
            index_status  = 'pending'
        """,
        (drive_file_id, name, mime_type, drive_path, size, modified_time),
    )
    row = conn.execute(
        "SELECT id FROM documents WHERE drive_file_id = ?", (drive_file_id,)
    ).fetchone()
    return row["id"]


def delete_pages(conn: sqlite3.Connection, document_id: int) -> None:
    """Delete all pages (and FTS entries) for a document before re-indexing."""
    rows = conn.execute(
        "SELECT id FROM pages WHERE document_id = ?", (document_id,)
    ).fetchall()
    for row in rows:
        conn.execute("DELETE FROM pages_fts WHERE rowid = ?", (row["id"],))
    conn.execute("DELETE FROM pages WHERE document_id = ?", (document_id,))


def insert_page(
    conn: sqlite3.Connection,
    document_id: int,
    page_number: int,
    text: str,
) -> None:
    normalized = normalize_tr(text)
    blob = compress(text)
    cur = conn.execute(
        "INSERT INTO pages (document_id, page_number, compressed_text) VALUES (?, ?, ?)",
        (document_id, page_number, blob),
    )
    page_id = cur.lastrowid
    conn.execute(
        "INSERT INTO pages_fts (rowid, body) VALUES (?, ?)",
        (page_id, normalized),
    )


def mark_indexed(conn: sqlite3.Connection, document_id: int, page_count: int) -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE documents
        SET index_status = 'indexed', indexed_at = ?, page_count = ?
        WHERE id = ?
        """,
        (now, page_count, document_id),
    )


def mark_failed(conn: sqlite3.Connection, document_id: int, reason: str) -> None:
    conn.execute(
        "UPDATE documents SET index_status = 'failed' WHERE id = ?",
        (document_id,),
    )


def delete_document(conn: sqlite3.Connection, drive_file_id: str) -> None:
    row = conn.execute(
        "SELECT id FROM documents WHERE drive_file_id = ?", (drive_file_id,)
    ).fetchone()
    if row:
        delete_pages(conn, row["id"])
        conn.execute("DELETE FROM documents WHERE id = ?", (row["id"],))


# ---------------------------------------------------------------------------
# Index read operations (search)
# ---------------------------------------------------------------------------

def is_index_ready(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM documents WHERE index_status = 'indexed'"
    ).fetchone()
    return row["cnt"] > 0


def search_fts(
    conn: sqlite3.Connection,
    query: str,
    mime_filter: Optional[str],
    folder_filter: Optional[str],
    max_results: int = 20,
    max_snippets_per_file: int = 3,
    context_chars: int = 150,
) -> List[dict]:
    norm_query = normalize_tr(query)
    results = []
    seen_files: dict = {}  # drive_file_id -> snippet count

    # --- 1. Filename matches (ranked first) ---
    filename_sql = """
        SELECT drive_file_id, name, mime_type, drive_path
        FROM documents
        WHERE index_status = 'indexed'
          AND lower(name) LIKE ?
    """
    params: list = [f"%{norm_query}%"]

    if mime_filter and mime_filter != "all":
        mime_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "other": None,
        }
        if mime_filter in ("pdf", "docx"):
            filename_sql += " AND mime_type = ?"
            params.append(mime_map[mime_filter])

    if folder_filter:
        filename_sql += " AND lower(drive_path) LIKE ?"
        params.append(f"%{normalize_tr(folder_filter)}%")

    filename_sql += " ORDER BY name LIMIT ?"
    params.append(max_results)

    for row in conn.execute(filename_sql, params).fetchall():
        if len(results) >= max_results:
            break
        fid = row["drive_file_id"]
        seen_files[fid] = 0
        results.append({
            "file_id": fid,
            "title": row["name"],
            "mime_type": row["mime_type"],
            "path": row["drive_path"],
            "page": None,
            "snippet": None,
            "match_type": "filename",
            "ocr_required": False,
        })

    # --- 2. FTS5 content matches ---
    fts_sql = """
        SELECT
            d.drive_file_id,
            d.name,
            d.mime_type,
            d.drive_path,
            p.page_number,
            p.compressed_text,
            p.id AS page_id
        FROM pages_fts
        JOIN pages p ON p.id = pages_fts.rowid
        JOIN documents d ON d.id = p.document_id
        WHERE pages_fts MATCH ?
          AND d.index_status = 'indexed'
    """
    fts_params: list = [norm_query]

    if mime_filter and mime_filter != "all":
        if mime_filter == "pdf":
            fts_sql += " AND d.mime_type = 'application/pdf'"
        elif mime_filter == "docx":
            fts_sql += " AND d.mime_type LIKE '%wordprocessingml%'"

    if folder_filter:
        fts_sql += " AND lower(d.drive_path) LIKE ?"
        fts_params.append(f"%{normalize_tr(folder_filter)}%")

    fts_sql += " ORDER BY bm25(pages_fts) LIMIT ?"
    fts_params.append(max_results * max_snippets_per_file)

    for row in conn.execute(fts_sql, fts_params).fetchall():
        if len(results) >= max_results:
            break

        fid = row["drive_file_id"]
        count = seen_files.get(fid, 0)
        if count >= max_snippets_per_file:
            continue

        # Extract snippet from compressed text
        snippet = None
        try:
            text = decompress(row["compressed_text"])
            snippet = _extract_snippet(text, query, context_chars)
        except Exception:
            snippet = None

        if fid not in seen_files or results[next(i for i, r in enumerate(results) if r["file_id"] == fid)]["match_type"] == "filename":
            # Don't re-add filename match as content match for same file
            if fid in seen_files and seen_files[fid] == 0 and any(r["file_id"] == fid and r["match_type"] == "filename" for r in results):
                seen_files[fid] = 1
                # Update the filename match result with page info if it's the only result
                continue

        seen_files[fid] = count + 1
        results.append({
            "file_id": fid,
            "title": row["name"],
            "mime_type": row["mime_type"],
            "path": row["drive_path"],
            "page": row["page_number"],
            "snippet": snippet,
            "match_type": "content",
            "ocr_required": False,
        })

    return results[:max_results]


def _extract_snippet(text: str, query: str, context_chars: int) -> Optional[str]:
    import re
    norm_text = normalize_tr(text)
    norm_query = normalize_tr(query)
    try:
        pattern = re.compile(re.escape(norm_query), re.IGNORECASE)
        match = pattern.search(norm_text)
        if not match:
            return None
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return " ".join(snippet.split())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def get_index_status(conn: sqlite3.Connection) -> dict:
    from datetime import datetime, timezone

    docs = conn.execute("SELECT COUNT(*) FROM documents WHERE index_status='indexed'").fetchone()[0]
    total_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    pages = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]

    db_size = get_db_path().stat().st_size if get_db_path().exists() else 0
    db_size_mb = round(db_size / 1024 / 1024, 1)

    last_sync_row = conn.execute(
        "SELECT finished_at FROM sync_log WHERE status='done' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    last_sync = last_sync_row["finished_at"] if last_sync_row else None

    if db_size > _SIZE_WARNING_BYTES:
        logger.warning("Index DB approaching 1.5 GB limit: %.1f MB", db_size_mb)

    return {
        "status": "ready" if docs > 0 else "empty",
        "documents_indexed": docs,
        "documents_total": total_docs,
        "pages": pages,
        "database_size_mb": db_size_mb,
        "last_sync": last_sync,
    }