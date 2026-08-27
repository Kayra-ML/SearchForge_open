import type {
  SearchResponse,
  FoldersResponse,
  DocumentMeta,
  MimeFilter,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function searchDocuments(
  query: string,
  mimeFilter: MimeFilter = "all",
  folderFilter?: string
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, type: mimeFilter });
  if (folderFilter) params.set("folder", folderFilter);
  return apiFetch<SearchResponse>(`/api/search?${params.toString()}`);
}

export async function getFolders(): Promise<FoldersResponse> {
  return apiFetch<FoldersResponse>("/api/folders");
}

export async function getDocumentMeta(fileId: string): Promise<DocumentMeta> {
  return apiFetch<DocumentMeta>(`/api/documents/${fileId}`);
}

export function getDocumentContentUrl(fileId: string): string {
  return `${API_BASE}/api/documents/${fileId}/content`;
}