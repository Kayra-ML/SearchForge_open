import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SearchForge",
  description: "Google Drive dokümanlarında hızlı arama sistemi",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body className="bg-surface-900 text-gray-100 min-h-screen font-sans antialiased">
        {children}
      </body>
    </html>
  );
}