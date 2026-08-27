"use client";

import Link from "next/link";
import type { SearchResult } from "@/types";

interface SearchResultProps {
  result: SearchResult;
  query: string;
}

function highlightText(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const parts = text.split(new RegExp(`(${escapeRegex(query)})`, "gi"));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={i}>{part}</mark>
    ) : (
      part
    )
  );
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function mimeLabel(mime: string): string {
  if (mime === "application/pdf") return "PDF";
  if (mime.includes("wordprocessingml") || mime.includes("msword")) return "DOCX";
  if (mime === "text/plain") return "TXT";
  return "DOC";
}

function MimeBadge({ mime }: { mime: string }) {
  const label = mimeLabel(mime);
  const isPdf = mime === "application/pdf";
  return (
    <span
      className={`text-xs font-mono font-semibold px-2 py-0.5 rounded border ${
        isPdf
          ? "bg-brand-950 border-brand-800 text-brand-400"
          : "bg-surface-600 border-surface-500 text-gray-400"
      }`}
    >
      {label}
    </span>
  );
}

export default function SearchResultCard({ result, query }: SearchResultProps) {
  const readerHref = `/document/${result.file_id}${result.page ? `?page=${result.page}` : ""}`;

  return (
    <div className="group bg-surface-800 border border-surface-600 rounded-xl p-5
                    hover:border-brand-700 transition-colors duration-150">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <MimeBadge mime={result.mime_type} />
            {result.page && (
              <span className="text-xs font-mono text-gray-500">
                sayfa {result.page}
              </span>
            )}
            {result.match_type === "filename" && (
              <span className="text-xs font-mono text-brand-500">dosya adı eşleşmesi</span>
            )}
          </div>

          <h3 className="font-semibold text-gray-100 text-sm leading-snug truncate mb-1">
            {highlightText(result.title, query)}
          </h3>

          {result.path && (
            <p className="text-xs font-mono text-gray-600 truncate mb-2">{result.path}</p>
          )}

          {result.ocr_required && (
            <p className="mt-1 text-xs font-mono text-yellow-600">
              [!] Taranmış PDF — metin araması desteklenmiyor
            </p>
          )}

          {result.snippet && !result.ocr_required && (
            <p className="mt-2 text-sm text-gray-400 leading-relaxed line-clamp-2">
              {highlightText(result.snippet, query)}
            </p>
          )}
        </div>

        <Link
          href={readerHref}
          className="flex-shrink-0 px-4 py-2 text-xs font-mono font-medium
                     bg-surface-700 border border-surface-500 text-gray-300 rounded-lg
                     group-hover:border-brand-600 group-hover:text-brand-400
                     hover:bg-surface-600 transition-colors duration-150"
        >
          Aç →
        </Link>
      </div>
    </div>
  );
}

export function SearchResultSkeleton() {
  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-5 animate-pulse">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex gap-2 mb-2">
            <div className="h-4 w-10 bg-surface-600 rounded" />
            <div className="h-4 w-16 bg-surface-600 rounded" />
          </div>
          <div className="h-4 bg-surface-600 rounded w-2/3 mb-2" />
          <div className="h-3 bg-surface-700 rounded w-1/3 mb-3" />
          <div className="h-3 bg-surface-700 rounded w-full mb-1" />
          <div className="h-3 bg-surface-700 rounded w-4/5" />
        </div>
        <div className="h-8 w-14 bg-surface-600 rounded-lg" />
      </div>
    </div>
  );
}