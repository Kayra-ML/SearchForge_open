"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { validateCredentials, setAuth, getAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (getAuth()) router.replace("/");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const ok = await validateCredentials(username.trim(), password);
      if (ok) {
        setAuth({ username: username.trim() });
        router.replace("/");
      } else {
        setError("Kullanıcı adı veya şifre hatalı.");
      }
    } catch {
      setError("Doğrulama sırasında bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-surface-900 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-10 text-center">
          <div className="inline-flex items-center gap-2 mb-4">
            <span className="text-brand-500 font-mono font-semibold text-2xl tracking-tight">
              &gt;_ SearchForge
            </span>
          </div>
          <p className="text-gray-500 text-sm font-mono">
            Güvenli Belge Arama Sistemi
          </p>
        </div>

        <div className="bg-surface-800 border border-surface-600 rounded-xl p-8">
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-brand-500" />
              <span className="text-xs font-mono text-gray-400 uppercase tracking-widest">
                Kimlik Doğrulama
              </span>
            </div>
            <div className="h-px bg-surface-600 mt-3" />
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1.5 uppercase tracking-wider">
                Kullanıcı Adı
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="kullanıcı_adı"
                autoFocus
                autoComplete="username"
                required
                disabled={loading}
                className="input-dark font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1.5 uppercase tracking-wider">
                Şifre
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                disabled={loading}
                className="input-dark font-mono"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 px-3 py-2.5 bg-red-950 border border-red-800 rounded-lg">
                <span className="text-red-400 font-mono text-xs">[HATA]</span>
                <span className="text-red-300 text-sm">{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !username.trim() || !password}
              className="mt-2 btn-primary w-full flex items-center justify-center gap-2 font-mono"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Doğrulanıyor...
                </>
              ) : (
                "Giriş Yap"
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-gray-600 font-mono">
          SearchForge v1.0 — Yetkisiz erişim yasaktır.
        </p>
      </div>
    </div>
  );
}