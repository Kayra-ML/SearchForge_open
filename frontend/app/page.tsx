"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import SearchBar from "@/components/SearchBar";
import SearchFilters from "@/components/SearchFilters";
import SearchResultCard, { SearchResultSkeleton } from "@/components/SearchResult";
import { searchDocuments, getFolders } from "@/lib/api";
import { getAuth, clearAuth } from "@/lib/auth";
import type { SearchResult, MimeFilter, FolderInfo } from "@/types";

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [mimeFilter, setMimeFilter] = useState<MimeFilter>("all");
  const [folderFilter, setFolderFilter] = useState("");
  const [folders, setFolders] = useState<FolderInfo[]>([]);
  const [username, setUsername] = useState("");

  useEffect(() => {
    const auth = getAuth();
    if (!auth) {
      router.replace("/login");
      return;
    }
    setUsername(auth.username);
    getFolders()
      .then((data) => setFolders(data.folders))
      .catch(() => {});
  }, [router]);

  function handleLogout() {
    clearAuth();
    router.replace("/login");
  }

  const handleSearch = useCallback(
    async (q: string) => {
      setQuery(q);
      setLoading(true);
      setError(null);
      setSearched(true);
      try {
        const data = await searchDocuments(q, mimeFilter, folderFilter || undefined);
        setResults(data.results);
        setTotal(data.total);
      } catch {
        setError("Arama sırasında bir hata oluştu. Lütfen tekrar deneyin.");
        setResults([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [mimeFilter, folderFilter]
  );

  return (
    <div className="min-h-screen flex flex-col bg-surface-900">
      <header className="bg-surface-800 border-b border-surface-600 px-4 py-3 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <span className="font-mono font-semibold text-brand-500 text-base shrink-0 tracking-tight">
            &gt;_ SF
          </span>
          <div className="flex-1">
            <SearchBar initialValue={query} onSearch={handleSearch} loading={loading} />
          </div>
          {username && (
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-xs font-mono text-gray-500 hidden sm:block">{username}</span>
              <button
                onClick={handleLogout}
                className="text-xs font-mono text-gray-500 hover:text-red-400 transition-colors"
              >
                çıkış
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-6">
        {!searched && (
          <div className="flex flex-col items-center justify-center py-28 text-center">
            <div className="mb-5 flex items-center justify-center w-16 h-16 rounded-2xl bg-surface-800 border border-surface-600">
              <svg className="h-8 w-8 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
              </svg>
            </div>
            <div className="mb-2">
              <span className="font-mono font-bold text-brand-500 text-3xl tracking-tight">
                SearchForge
              </span>
            </div>
            <p className="text-gray-500 text-sm font-mono mb-10">
              Belge deposunda arama yapın
            </p>
            <div className="w-full max-w-xl">
              <SearchBar onSearch={handleSearch} loading={loading} />
            </div>
            <p className="mt-4 text-xs font-mono text-gray-700">
              PDF, DOCX ve metin dosyalarında tam metin arama
            </p>
          </div>
        )}

        {searched && (
          <>
            <div className="mb-4 flex items-center justify-between flex-wrap gap-3">
              <SearchFilters
                mimeFilter={mimeFilter}
                onMimeChange={(f) => setMimeFilter(f)}
                folderFilter={folderFilter}
                onFolderChange={(f) => setFolderFilter(f)}
                folders={folders}
              />
              {!loading && (
                <span className="text-xs font-mono text-gray-500">
                  {total} sonuç
                </span>
              )}
            </div>

            {error && (
              <div className="flex items-center gap-2 px-4 py-3 bg-red-950 border border-red-800 rounded-lg mb-4">
                <span className="font-mono text-red-400 text-xs">[HATA]</span>
                <span className="text-red-300 text-sm">{error}</span>
              </div>
            )}

            {loading && (
              <div className="flex flex-col gap-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <SearchResultSkeleton key={i} />
                ))}
              </div>
            )}

            {!loading && !error && results.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="text-4xl font-mono text-gray-700 mb-3">[ ]</div>
                <p className="font-mono text-gray-400 text-sm font-medium">Sonuç bulunamadı</p>
                <p className="text-xs font-mono text-gray-600 mt-1">
                  &quot;{query}&quot; için eşleşme yok — farklı bir ifade deneyin
                </p>
              </div>
            )}

            {!loading && !error && results.length > 0 && (
              <div className="flex flex-col gap-3">
                {results.map((result, idx) => (
                  <SearchResultCard
                    key={`${result.file_id}-${result.page}-${idx}`}
                    result={result}
                    query={query}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}