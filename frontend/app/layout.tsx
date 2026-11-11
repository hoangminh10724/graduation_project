import "./globals.css";
import type { ReactNode } from "react";

export const metadata = { title: "WordSpeak" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body className="min-h-screen bg-slate-50 text-slate-900">{children}</body>
    </html>
  );
}
