"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import PdfViewer from "@/components/PdfViewer";
import { getDocumentMeta, getDocumentContentUrl } from "@/lib/api";
import { getAuth } from "@/lib/auth";
import type { DocumentMeta } from "@/types";

export default function DocumentPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const fileId = params.id as string;
  const initialPage = parseInt(searchParams.get("page") || "1", 10);

  const [meta, setMeta] = useState<DocumentMeta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getAuth()) {
      router.replace("/login");
      return;
    }
    if (!fileId) return;
    getDocumentMeta(fileId)
      .then(setMeta)
      .catch(() => setError("Doküman bilgisi alınamadı."))
      .finally(() => setLoading(false));
  }, [fileId, router]);

  const contentUrl = getDocumentContentUrl(fileId);

  return (
    <div className="flex flex-col h-screen bg-surface-900">
      <header className="bg-surface-800 border-b border-surface-600 px-4 py-3 flex items-center gap-4 shrink-0">
        <Link
          href="/"
          className="text-xs font-mono text-gray-500 hover:text-brand-400 transition-colors flex items-center gap-1 shrink-0"
        >
          ← Geri
        </Link>

        <div className="h-4 w-px bg-surface-600 shrink-0" />

        {loading && (
          <div className="h-3.5 w-48 bg-surface-600 rounded animate-pulse" />
        )}

        {meta && (
          <div className="flex-1 min-w-0">
            <h1 className="font-mono font-medium text-gray-200 truncate text-sm">
              {meta.title}
            </h1>
            {meta.path && (
              <p className="text-xs font-mono text-gray-600 truncate">{meta.path}</p>
            )}
          </div>
        )}

        {error && (
          <span className="text-xs font-mono text-red-400">[HATA] {error}</span>
        )}

        {meta && (
          <div className="shrink-0 flex items-center gap-3">
            {meta.size && (
              <span className="text-xs font-mono text-gray-600 hidden sm:block">
                {(meta.size / 1024 / 1024).toFixed(1)} MB
              </span>
            )}
            <span className="text-xs font-mono px-2 py-0.5 bg-brand-950 border border-brand-800 text-brand-400 rounded">
              PDF
            </span>
          </div>
        )}
      </header>

      <div className="flex-1 overflow-hidden">
        {!loading && !error && (
          <PdfViewer url={contentUrl} initialPage={initialPage} />
        )}

        {loading && (
          <div className="flex items-center justify-center h-full gap-3 text-gray-500 font-mono text-sm">
            <svg className="animate-spin h-5 w-5 text-brand-500" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Yükleniyor...
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <p className="font-mono text-red-400 text-sm">[HATA] {error}</p>
            <Link href="/" className="text-xs font-mono text-brand-500 hover:text-brand-400 transition-colors">
              ← Ana sayfaya dön
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}