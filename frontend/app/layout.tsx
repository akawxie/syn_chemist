import type { Metadata } from "next";
import { LanguageProvider } from "@/components/LanguageContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI_chemist",
  description: "AI-assisted workflow for synthetic chemists — judge + verify pipeline.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-gray-100 antialiased">
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
