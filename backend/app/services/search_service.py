"""
Search service — SQLite FTS5 only.

NO Google Drive calls during search.
NO PDF downloads during search.
NO PyMuPDF during search.
"""

import logging
from typing import List, Optional

from app.core.config import get_settings
from app.models.search import SearchResult, MatchType
from app.services.cache_service import get_cache
from app.services.index_service import (
    get_connection,
    is_index_ready,
    search_fts,
)

logger = logging.getLogger(__name__)


class IndexNotReadyError(Exception):
    pass


async def search(
    query: str,
    mime_filter: Optional[str] = None,
    folder_filter: Optional[str] = None,
) -> List[SearchResult]:
    settings = get_settings()
    cache = get_cache()
    cache_key = f"fts:{query}:{mime_filter}:{folder_filter}"

    cached = cache.get(cache_key)
    if cached is not None:
        logger.info("Cache hit for query: %s", query)
        return cached

    conn = get_connection()
    try:
        if not is_index_ready(conn):
            raise IndexNotReadyError(
                "Search index is not ready. Run: python -m app.scripts.sync_index"
            )

        raw = search_fts(
            conn=conn,
            query=query,
            mime_filter=mime_filter,
            folder_filter=folder_filter,
            max_results=settings.SEARCH_RESULT_LIMIT,
            max_snippets_per_file=settings.MAX_SNIPPETS_PER_FILE,
            context_chars=settings.SNIPPET_CONTEXT_CHARS,
        )
    finally:
        conn.close()

    results = [
        SearchResult(
            file_id=r["file_id"],
            title=r["title"],
            mime_type=r["mime_type"],
            path=r["path"],
            page=r["page"],
            snippet=r["snippet"],
            match_type=MatchType(r["match_type"]),
            ocr_required=r.get("ocr_required", False),
        )
        for r in raw
    ]

    logger.info("Search '%s' → %d results (no Drive calls)", query, len(results))
    cache.set(cache_key, results)
    return results