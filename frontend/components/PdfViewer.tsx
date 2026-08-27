"use client";

import { useEffect, useRef, useState } from "react";

interface PdfViewerProps {
  url: string;
  initialPage?: number;
}

export default function PdfViewer({ url, initialPage = 1 }: PdfViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdf, setPdf] = useState<any>(null);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.2);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inputPage, setInputPage] = useState(String(initialPage));
  const renderTaskRef = useRef<any>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPdf() {
      setLoading(true);
      setError(null);
      try {
        const pdfjsLib = await import("pdfjs-dist");
        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        const loadingTask = pdfjsLib.getDocument({ url, withCredentials: false });
        const pdfDoc = await loadingTask.promise;
        if (cancelled) return;
        setPdf(pdfDoc);
        setTotalPages(pdfDoc.numPages);
        setLoading(false);
      } catch {
        if (!cancelled) {
          setError("PDF yüklenirken bir hata oluştu.");
          setLoading(false);
        }
      }
    }

    loadPdf();
    return () => { cancelled = true; };
  }, [url]);

  useEffect(() => {
    if (!pdf || !canvasRef.current) return;
    let cancelled = false;

    async function renderPage() {
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }
      const page = await pdf.getPage(currentPage);
      if (cancelled) return;

      const viewport = page.getViewport({ scale });
      const canvas = canvasRef.current!;
      const ctx = canvas.getContext("2d")!;
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      const renderTask = page.render({ canvasContext: ctx, viewport });
      renderTaskRef.current = renderTask;
      await renderTask.promise;
    }

    renderPage().catch(() => {});
    return () => { cancelled = true; };
  }, [pdf, currentPage, scale]);

  function goToPage(n: number) {
    const clamped = Math.max(1, Math.min(n, totalPages));
    setCurrentPage(clamped);
    setInputPage(String(clamped));
  }

  function handlePageInput(e: React.FormEvent) {
    e.preventDefault();
    const n = parseInt(inputPage, 10);
    if (!isNaN(n)) goToPage(n);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 font-mono text-sm gap-3">
        <svg className="animate-spin h-5 w-5 text-brand-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        Doküman yükleniyor...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <span className="font-mono text-red-400 text-sm">[HATA] {error}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 bg-surface-800 border-b border-surface-600 gap-3 flex-wrap shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage <= 1}
            className="px-3 py-1.5 text-xs font-mono bg-surface-700 border border-surface-500
                       text-gray-300 rounded hover:border-brand-600 hover:text-brand-400
                       disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            ← Önceki
          </button>

          <form onSubmit={handlePageInput} className="flex items-center gap-1.5">
            <input
              type="number"
              min={1}
              max={totalPages}
              value={inputPage}
              onChange={(e) => setInputPage(e.target.value)}
              className="w-14 text-center text-xs font-mono bg-surface-700 border border-surface-500
                         text-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-brand-600
                         focus:ring-1 focus:ring-brand-600 transition-colors"
            />
            <span className="text-xs font-mono text-gray-500">/ {totalPages}</span>
          </form>

          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="px-3 py-1.5 text-xs font-mono bg-surface-700 border border-surface-500
                       text-gray-300 rounded hover:border-brand-600 hover:text-brand-400
                       disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Sonraki →
          </button>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setScale((s) => Math.max(0.5, +(s - 0.25).toFixed(2)))}
            title="Uzaklaştır (−)"
            className="w-9 h-9 flex items-center justify-center font-mono text-lg
                       bg-surface-700 border border-surface-500 text-gray-300 rounded-lg
                       hover:border-brand-600 hover:text-brand-400 active:scale-95 transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0zM8 11h6" />
            </svg>
          </button>
          <button
            onClick={() => setScale(1.2)}
            title="Sıfırla"
            className="px-2 h-9 text-xs font-mono bg-surface-700 border border-surface-500
                       text-gray-300 rounded-lg hover:border-brand-600 hover:text-brand-400
                       active:scale-95 transition-all min-w-[52px]"
          >
            {Math.round(scale * 100)}%
          </button>
          <button
            onClick={() => setScale((s) => Math.min(3, +(s + 0.25).toFixed(2)))}
            title="Yaklaştır (+)"
            className="w-9 h-9 flex items-center justify-center font-mono text-lg
                       bg-surface-700 border border-surface-500 text-gray-300 rounded-lg
                       hover:border-brand-600 hover:text-brand-400 active:scale-95 transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0zM11 8v6M8 11h6" />
            </svg>
          </button>
          <button
            onClick={() => setScale(1.8)}
            title="Geniş Görünüm"
            className="w-9 h-9 flex items-center justify-center
                       bg-surface-700 border border-surface-500 text-gray-400 rounded-lg
                       hover:border-brand-600 hover:text-brand-400 active:scale-95 transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto flex justify-center bg-surface-900 p-6">
        <canvas
          ref={canvasRef}
          className="shadow-2xl"
          style={{ maxWidth: "100%", height: "auto" }}
        />
      </div>
    </div>
  );
}