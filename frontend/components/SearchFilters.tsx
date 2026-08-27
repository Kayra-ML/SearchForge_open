"use client";

import type { MimeFilter, FolderInfo } from "@/types";

interface SearchFiltersProps {
  mimeFilter: MimeFilter;
  onMimeChange: (filter: MimeFilter) => void;
  folderFilter: string;
  onFolderChange: (folder: string) => void;
  folders: FolderInfo[];
}

const MIME_OPTIONS: { label: string; value: MimeFilter }[] = [
  { label: "Tümü", value: "all" },
  { label: "PDF", value: "pdf" },
  { label: "DOCX", value: "docx" },
  { label: "Diğer", value: "other" },
];

export default function SearchFilters({
  mimeFilter,
  onMimeChange,
  folderFilter,
  onFolderChange,
  folders,
}: SearchFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1 bg-surface-800 border border-surface-600 rounded-lg p-1">
        {MIME_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onMimeChange(opt.value)}
            className={`px-3 py-1.5 text-xs font-mono font-medium rounded-md transition-colors duration-150 ${
              mimeFilter === opt.value
                ? "bg-brand-600 text-white"
                : "text-gray-400 hover:text-gray-200 hover:bg-surface-600"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {folders.length > 0 && (
        <select
          value={folderFilter}
          onChange={(e) => onFolderChange(e.target.value)}
          className="px-3 py-2 text-xs font-mono bg-surface-800 border border-surface-600 rounded-lg
                     text-gray-300 focus:outline-none focus:border-brand-600 focus:ring-1 focus:ring-brand-600
                     transition-colors duration-150 max-w-xs"
        >
          <option value="">Tüm Klasörler</option>
          {folders.map((f) => (
            <option key={f.id} value={f.path}>
              {f.path || f.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}