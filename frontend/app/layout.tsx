import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Provider } from "@/components/provider";
import { Shell } from "@/components/shell";

export const metadata: Metadata = {
  title: { default: "WordSpeak", template: "%s · WordSpeak" },
  description: "Luyện ngữ âm, ngữ điệu và hội thoại tiếng Anh cho người Việt.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body>
        <Provider>
          <Shell>{children}</Shell>
        </Provider>
      </body>
    </html>
  );
}
