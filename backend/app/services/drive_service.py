import io
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import List, Optional, Set, Tuple

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

from app.core.config import get_settings
from app.models.search import DriveFile, FolderInfo

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

MIME_FOLDER = "application/vnd.google-apps.folder"

MIME_TYPE_MAP = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "text/plain": "txt",
}

MAX_FOLDER_DEPTH = 10
FOLDERS_TIMEOUT_SECONDS = 120
FILES_TIMEOUT_SECONDS = 180

# Thread-local storage: each thread gets its own Drive service instance
_thread_local = threading.local()

# Simple in-memory caches (key -> (value, timestamp))
_folders_cache: Optional[Tuple[List[FolderInfo], float]] = None
_files_cache: Optional[Tuple[Tuple[List[DriveFile], List[FolderInfo]], float]] = None
_CACHE_TTL = 300  # seconds


def _build_service():
    """Return a Drive service for the current thread (thread-local, not shared)."""
    if not hasattr(_thread_local, "service") or _thread_local.service is None:
        settings = get_settings()
        sa_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE

        if not Path(sa_file).exists():
            raise FileNotFoundError(
                "Service account file not found. "
                "Place your credential JSON at the configured path and set "
                "GOOGLE_SERVICE_ACCOUNT_FILE in backend/.env"
            )

        creds = service_account.Credentials.from_service_account_file(
            sa_file,
            scopes=SCOPES,
        )
        _thread_local.service = build("drive", "v3", credentials=creds, cache_discovery=False)

    return _thread_local.service


def check_drive_connection() -> bool:
    try:
        settings = get_settings()
        service = _build_service()
        result = service.files().get(
            fileId=settings.GOOGLE_DRIVE_FOLDER_ID,
            fields="id, name, mimeType",
        ).execute()
        logger.info("Drive connection OK — root folder: %s", result.get("name"))
        return True
    except FileNotFoundError as e:
        logger.error("Drive connection failed — credential file missing: %s", str(e))
        return False
    except Exception as e:
        logger.error("Drive connection failed: %s", type(e).__name__)
        return False


# ---------------------------------------------------------------------------
# Folders-only traversal (fast — only queries folder MIME type)
# ---------------------------------------------------------------------------

def _fetch_subfolders(folder_id: str) -> List[dict]:
    """
    Fetch all direct subfolder items for a given folder_id.
    Builds its own Drive service so it is safe to call from any thread.
    """
    service = _build_service()
    items = []
    page_token = None
    while True:
        response = service.files().list(
            q=(
                f"'{folder_id}' in parents "
                f"and mimeType = 'application/vnd.google-apps.folder' "
                f"and trashed = false"
            ),
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
            pageSize=1000,
        ).execute()
        items.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return items


def _collect_folders_sync(root_folder_id: str) -> List[FolderInfo]:
    """
    BFS traversal using a thread pool to fetch multiple folders in parallel.
    Each thread builds its own service instance (thread-safe).
    Only queries folder mimeType — never reads file content.
    Uses a visited set to prevent cycles.
    """
    folders: List[FolderInfo] = []
    visited: Set[str] = {root_folder_id}

    queue: List[Tuple[str, str, int]] = [(root_folder_id, "", 0)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        while queue:
            next_queue: List[Tuple[str, str, int]] = []
            batch = [(fid, path, depth) for fid, path, depth in queue if depth < MAX_FOLDER_DEPTH]
            for _, path, _ in [x for x in queue if x[2] >= MAX_FOLDER_DEPTH]:
                logger.warning("Max folder depth reached at: %s", path)

            if not batch:
                break

            futures = {
                pool.submit(_fetch_subfolders, fid): (fid, path, depth)
                for fid, path, depth in batch
            }

            for future, (parent_id, parent_path, depth) in futures.items():
                try:
                    items = future.result(timeout=30)
                except Exception as exc:
                    logger.error("Failed to fetch subfolders for %s: %s", parent_id, exc)
                    continue

                for item in items:
                    fid = item["id"]
                    name = item.get("name", "")
                    if fid in visited:
                        logger.warning("Cycle detected — skipping folder id: %s", fid)
                        continue
                    visited.add(fid)
                    sub_path = f"{parent_path}/{name}" if parent_path else name
                    logger.info("Scanning folder: %s (%s)", name, fid)
                    folders.append(FolderInfo(id=fid, name=name, path=sub_path))
                    next_queue.append((fid, sub_path, depth + 1))

            queue = next_queue

    logger.info("Folder traversal complete — total folders found: %d", len(folders))
    return folders


def list_folders() -> List[FolderInfo]:
    """
    Return all subfolders under the configured root. Results are cached.
    Must be called from a thread (e.g. via run_in_executor) — never blocks the event loop.
    Raises TimeoutError if Drive takes too long.
    """
    global _folders_cache

    if _folders_cache is not None:
        cached_folders, ts = _folders_cache
        if time.time() - ts < _CACHE_TTL:
            logger.info("Returning folders from cache (%d items)", len(cached_folders))
            return cached_folders

    settings = get_settings()
    root_id = settings.GOOGLE_DRIVE_FOLDER_ID

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_collect_folders_sync, root_id)
    try:
        folders = future.result(timeout=FOLDERS_TIMEOUT_SECONDS)
    except FuturesTimeoutError:
        executor.shutdown(wait=False)
        raise TimeoutError(
            f"Folder traversal timed out after {FOLDERS_TIMEOUT_SECONDS}s"
        )
    except Exception:
        executor.shutdown(wait=False)
        raise
    finally:
        executor.shutdown(wait=False)

    _folders_cache = (folders, time.time())
    return folders


# ---------------------------------------------------------------------------
# Full file + folder traversal (used by search)
# ---------------------------------------------------------------------------

def _fetch_folder_contents(folder_id: str) -> List[dict]:
    """Fetch all direct children (files + folders) for a given folder_id."""
    service = _build_service()
    items = []
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            pageToken=page_token,
            pageSize=1000,
        ).execute()
        items.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return items


def _collect_all_files_sync(root_folder_id: str) -> Tuple[List[DriveFile], List[FolderInfo]]:
    """
    BFS traversal using a thread pool to fetch multiple folders in parallel.
    Never downloads file content. Thread-safe via thread-local service instances.
    """
    files: List[DriveFile] = []
    folders: List[FolderInfo] = []
    visited: Set[str] = {root_folder_id}

    queue: List[Tuple[str, str, int]] = [(root_folder_id, "", 0)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        while queue:
            batch = [(fid, path, depth) for fid, path, depth in queue if depth < MAX_FOLDER_DEPTH]
            for _, path, _ in [x for x in queue if x[2] >= MAX_FOLDER_DEPTH]:
                logger.warning("Max folder depth reached at: %s", path)

            if not batch:
                break

            next_queue: List[Tuple[str, str, int]] = []
            futures = {
                pool.submit(_fetch_folder_contents, fid): (fid, path, depth)
                for fid, path, depth in batch
            }

            for future, (parent_id, parent_path, depth) in futures.items():
                try:
                    items = future.result(timeout=30)
                except Exception as exc:
                    logger.error("Failed to fetch contents for %s: %s", parent_id, exc)
                    continue

                for item in items:
                    fid = item["id"]
                    name = item.get("name", "")
                    mime = item.get("mimeType", "")

                    if mime == MIME_FOLDER:
                        if fid in visited:
                            logger.warning("Cycle detected — skipping folder id: %s", fid)
                            continue
                        visited.add(fid)
                        sub_path = f"{parent_path}/{name}" if parent_path else name
                        folders.append(FolderInfo(id=fid, name=name, path=sub_path))
                        next_queue.append((fid, sub_path, depth + 1))

                    elif mime in MIME_TYPE_MAP:
                        files.append(DriveFile(
                            drive_file_id=fid,
                            name=name,
                            mime_type=mime,
                            size=int(item["size"]) if item.get("size") else None,
                            modified_time=item.get("modifiedTime"),
                            parent_folder=parent_path if parent_path else "root",
                            drive_path=f"{parent_path}/{name}" if parent_path else name,
                        ))

            queue = next_queue

    logger.info(
        "Full traversal complete — files: %d, folders: %d",
        len(files), len(folders),
    )
    return files, folders


def list_all_files() -> Tuple[List[DriveFile], List[FolderInfo]]:
    """
    Return all files and folders under the configured root. Results are cached.
    Raises TimeoutError if Drive takes too long.
    """
    global _files_cache

    if _files_cache is not None:
        cached_result, ts = _files_cache
        if time.time() - ts < _CACHE_TTL:
            files, folders = cached_result
            logger.info(
                "Returning files from cache — files: %d, folders: %d",
                len(files), len(folders),
            )
            return cached_result

    settings = get_settings()
    root_id = settings.GOOGLE_DRIVE_FOLDER_ID

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_collect_all_files_sync, root_id)
    try:
        result = future.result(timeout=FILES_TIMEOUT_SECONDS)
    except FuturesTimeoutError:
        executor.shutdown(wait=False)
        raise TimeoutError(
            f"File traversal timed out after {FILES_TIMEOUT_SECONDS}s"
        )
    except Exception:
        executor.shutdown(wait=False)
        raise
    finally:
        executor.shutdown(wait=False)

    _files_cache = (result, time.time())
    return result


# ---------------------------------------------------------------------------
# Single file operations
# ---------------------------------------------------------------------------

def get_file_metadata(file_id: str) -> Optional[DriveFile]:
    try:
        service = _build_service()
        item = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, size, modifiedTime",
        ).execute()
        return DriveFile(
            drive_file_id=item["id"],
            name=item["name"],
            mime_type=item.get("mimeType", ""),
            size=int(item["size"]) if item.get("size") else None,
            modified_time=item.get("modifiedTime"),
            parent_folder=None,
            drive_path=item["name"],
        )
    except Exception as e:
        logger.error("Failed to get file metadata: %s", type(e).__name__)
        return None


def verify_file_in_folder(file_id: str) -> bool:
    """Verify that file_id belongs to the configured root folder (recursively)."""
    try:
        all_files, _ = list_all_files()
        return any(f.drive_file_id == file_id for f in all_files)
    except Exception as e:
        logger.error("Failed to verify file in folder: %s", type(e).__name__)
        return False


def download_file_to_buffer(file_id: str) -> Optional[bytes]:
    try:
        service = _build_service()
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request, chunksize=1024 * 1024 * 5)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        logger.error("Failed to download file: %s", type(e).__name__)
        return None