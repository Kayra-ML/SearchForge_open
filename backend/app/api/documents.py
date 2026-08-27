import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.core.security import validate_file_id
from app.models.search import DocumentMeta, FoldersResponse
from app.services.drive_service import (
    get_file_metadata,
    verify_file_in_folder,
    download_file_to_buffer,
    list_folders,
)
from app.services.cache_service import get_cache

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documents/{file_id}", response_model=DocumentMeta)
async def get_document_metadata(file_id: str):
    file_id = validate_file_id(file_id)

    if not verify_file_in_folder(file_id):
        raise HTTPException(status_code=403, detail="Access denied")

    meta = get_file_metadata(file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentMeta(
        file_id=meta.drive_file_id,
        title=meta.name,
        mime_type=meta.mime_type,
        path=meta.drive_path,
        size=meta.size,
        modified_time=meta.modified_time,
    )


@router.get("/documents/{file_id}/content")
async def get_document_content(file_id: str, request: Request):
    file_id = validate_file_id(file_id)

    if not verify_file_in_folder(file_id):
        raise HTTPException(status_code=403, detail="Access denied")

    meta = get_file_metadata(file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found")

    cache = get_cache()
    cache_key = f"pdf_bytes:{file_id}"
    pdf_bytes = cache.get(cache_key)

    if pdf_bytes is None:
        pdf_bytes = download_file_to_buffer(file_id)
        if not pdf_bytes:
            raise HTTPException(status_code=502, detail="Failed to retrieve document")
        cache.set(cache_key, pdf_bytes)

    file_size = len(pdf_bytes)
    range_header = request.headers.get("Range")

    if range_header:
        try:
            range_value = range_header.strip().replace("bytes=", "")
            parts = range_value.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
            end = min(end, file_size - 1)

            chunk = pdf_bytes[start:end + 1]

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(chunk)),
                "Content-Type": meta.mime_type,
                "Content-Disposition": "inline",
            }

            return StreamingResponse(
                iter([chunk]),
                status_code=206,
                headers=headers,
                media_type=meta.mime_type,
            )
        except Exception as e:
            logger.error("Range request error: %s", type(e).__name__)

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Disposition": "inline",
    }

    return StreamingResponse(
        iter([pdf_bytes]),
        status_code=200,
        headers=headers,
        media_type=meta.mime_type,
    )


@router.get("/folders", response_model=FoldersResponse)
async def get_folders():
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        folders = await loop.run_in_executor(None, list_folders)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Folder listing timed out")
    except Exception as e:
        logger.error("Folder listing failed: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to list folders")
    return FoldersResponse(folders=folders)