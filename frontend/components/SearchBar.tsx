"use client";

import { useState } from "react";

interface SearchBarProps {
  initialValue?: string;
  onSearch: (query: string) => void;
  loading?: boolean;
}

export default function SearchBar({ initialValue = "", onSearch, loading }: SearchBarProps) {
  const [value, setValue] = useState(initialValue);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed) onSearch(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <svg
            className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
          </svg>
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Aranacak kelime veya ifade..."
            disabled={loading}
            autoFocus
            className="w-full bg-surface-700 border border-surface-500 rounded-lg pl-10 pr-4 py-3
                       text-gray-100 placeholder-gray-600 text-sm font-mono
                       focus:outline-none focus:border-brand-600 focus:ring-1 focus:ring-brand-600
                       disabled:opacity-50 transition-colors duration-150"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="btn-primary px-5 font-mono flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Aranıyor
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
              </svg>
              Ara
            </>
          )}
        </button>
      </div>
    </form>
  );
}