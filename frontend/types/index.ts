export type MatchType = "filename" | "content";
export type MimeFilter = "all" | "pdf" | "docx" | "other";

export interface SearchResult {
  file_id: string;
  title: string;
  mime_type: string;
  path: string;
  page: number | null;
  snippet: string | null;
  match_type: MatchType;
  ocr_required: boolean;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
}

export interface FolderInfo {
  id: string;
  name: string;
  path: string;
}

export interface FoldersResponse {
  folders: FolderInfo[];
}

export interface DocumentMeta {
  file_id: string;
  title: string;
  mime_type: string;
  path: string;
  size: number | null;
  modified_time: string | null;
  ocr_required: boolean;
}