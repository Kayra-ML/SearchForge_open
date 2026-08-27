from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class MatchType(str, Enum):
    filename = "filename"
    content = "content"


class MimeTypeFilter(str, Enum):
    all = "all"
    pdf = "pdf"
    docx = "docx"
    other = "other"


class SearchResult(BaseModel):
    file_id: str
    title: str
    mime_type: str
    path: str
    page: Optional[int] = None
    snippet: Optional[str] = None
    match_type: MatchType
    ocr_required: bool = False


class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResult]


class DriveFile(BaseModel):
    drive_file_id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    modified_time: Optional[str] = None
    parent_folder: Optional[str] = None
    drive_path: str


class FolderInfo(BaseModel):
    id: str
    name: str
    path: str


class FoldersResponse(BaseModel):
    folders: List[FolderInfo]


class DocumentMeta(BaseModel):
    file_id: str
    title: str
    mime_type: str
    path: str
    size: Optional[int] = None
    modified_time: Optional[str] = None
    ocr_required: bool = False