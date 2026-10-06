import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SageCommand Air Power System — Aero",
  description: "Next-Generation Air Operations Command & Decision Governance Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-obsidian-900 text-slate-200 antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}
