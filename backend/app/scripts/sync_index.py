"""
Index sync script.

Usage:
    python -m app.scripts.sync_index [--limit N] [--force]

Options:
    --limit N   Only process first N PDFs (for pilot testing)
    --force     Re-index all files even if unchanged
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Ensure backend/ is on the path when run as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Google Drive PDFs to SQLite FTS5 index")
    parser.add_argument("--limit", type=int, default=None, help="Max number of PDFs to index")
    parser.add_argument("--force", action="store_true", help="Re-index even unchanged files")
    args = parser.parse_args()

    from app.services.index_service import (
        init_db, get_connection, get_db_path,
        upsert_document, delete_pages, insert_page,
        mark_indexed, mark_failed, delete_document,
        get_index_status,
    )
    from app.services.drive_service import list_all_files

    try:
        import fitz
    except ImportError:
        logger.error("PyMuPDF (fitz) is not installed. Run: pip install pymupdf")
        sys.exit(1)

    logger.info("Initializing index database...")
    init_db()

    logger.info("Fetching file list from Google Drive...")
    t0 = time.monotonic()
    all_files, _ = list_all_files()
    elapsed = time.monotonic() - t0
    logger.info("Drive traversal complete: %d files found in %.1fs", len(all_files), elapsed)

    pdf_files = [f for f in all_files if f.mime_type == "application/pdf"]
    logger.info("PDF files found: %d", len(pdf_files))

    if args.limit:
        pdf_files = pdf_files[:args.limit]
        logger.info("Limit applied: processing first %d PDFs", len(pdf_files))

    conn = get_connection()

    # Build a set of drive_file_ids currently in Drive
    drive_ids = {f.drive_file_id for f in all_files}

    # Remove docs from index that no longer exist in Drive
    existing_in_db = conn.execute("SELECT drive_file_id FROM documents").fetchall()
    removed = 0
    for row in existing_in_db:
        if row["drive_file_id"] not in drive_ids:
            delete_document(conn, row["drive_file_id"])
            removed += 1
    if removed:
        conn.commit()
        logger.info("Removed %d documents no longer in Drive", removed)

    # Sync log
    started_at = datetime.now(timezone.utc).isoformat()
    log_id = conn.execute(
        "INSERT INTO sync_log (started_at, files_total, status) VALUES (?, ?, 'running')",
        (started_at, len(pdf_files)),
    ).lastrowid
    conn.commit()

    total = len(pdf_files)
    indexed_count = 0
    skipped_count = 0
    failed_count = 0

    for i, f in enumerate(pdf_files, start=1):
        prefix = f"[{i}/{total}]"

        # Check if unchanged
        if not args.force:
            existing = conn.execute(
                "SELECT modified_time, index_status FROM documents WHERE drive_file_id = ?",
                (f.drive_file_id,),
            ).fetchone()
            if (
                existing
                and existing["index_status"] == "indexed"
                and existing["modified_time"] == f.modified_time
            ):
                logger.info("%s skipped unchanged: %s", prefix, f.name)
                skipped_count += 1
                continue

        # Upsert document metadata
        doc_id = upsert_document(
            conn,
            drive_file_id=f.drive_file_id,
            name=f.name,
            mime_type=f.mime_type,
            drive_path=f.drive_path,
            size=f.size,
            modified_time=f.modified_time,
        )
        conn.commit()

        # Download and index
        try:
            _index_pdf(conn, f, doc_id, prefix)
            indexed_count += 1
        except Exception as e:
            logger.error("%s failed: %s — %s", prefix, f.name, e)
            mark_failed(conn, doc_id, str(e))
            conn.commit()
            failed_count += 1
            continue

    # Finish sync log
    finished_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE sync_log SET finished_at=?, files_indexed=?, files_skipped=?, files_failed=?, status='done'
        WHERE id=?
        """,
        (finished_at, indexed_count, skipped_count, failed_count, log_id),
    )
    conn.commit()

    # Final report
    status = get_index_status(conn)
    conn.close()

    logger.info("=" * 60)
    logger.info("Sync complete")
    logger.info("  Indexed : %d", indexed_count)
    logger.info("  Skipped : %d", skipped_count)
    logger.info("  Failed  : %d", failed_count)
    logger.info("  Documents in index : %d", status["documents_indexed"])
    logger.info("  Pages in index     : %d", status["pages"])
    logger.info("  DB size            : %.1f MB", status["database_size_mb"])


def _index_pdf(conn, f, doc_id: int, prefix: str) -> None:
    """Download PDF, extract text page by page, write to index. Temp file always cleaned up."""
    import fitz
    from app.services.drive_service import download_file_to_buffer
    from app.services.index_service import delete_pages, insert_page, mark_indexed

    logger.info("%s indexing: %s", prefix, f.name)

    pdf_bytes = download_file_to_buffer(f.drive_file_id)
    if not pdf_bytes:
        raise RuntimeError("Download returned empty bytes")

    delete_pages(conn, doc_id)

    page_count = 0
    text_pages = 0

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            text = doc[page_num].get_text()
            if text.strip():
                text_pages += 1
                insert_page(conn, doc_id, page_num + 1, text)
            page_count += 1
        doc.close()
    except Exception as e:
        raise RuntimeError(f"PyMuPDF error: {e}") from e
    finally:
        pdf_bytes = None  # release memory

    conn.commit()
    mark_indexed(conn, doc_id, page_count)
    conn.commit()

    logger.info(
        "%s indexed: %s — %d pages (%d with text)",
        prefix, f.name, page_count, text_pages,
    )


if __name__ == "__main__":
    main()