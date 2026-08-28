import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Auteur — The Film Bible Agent",
  description:
    "AI cinema's memory. Grounded in reality. Consistent across every shot. An agentic AI film studio that maintains a persistent, research-grounded Film Bible and enforces cross-shot consistency across every generation call. (Agentic Cinema Hackathon — Parallel Partner Track)",
  keywords: [
    "Auteur",
    "Film Bible",
    "Veo 3.1",
    "cross-shot consistency",
    "agentic cinema",
    "Google Cloud",
    "Parallel Search",
    "Agentic Cinema Hackathon",
  ],
  authors: [{ name: "Auteur" }],
  openGraph: {
    title: "Auteur — The Film Bible Agent",
    description:
      "AI cinema's memory. Grounded in reality. Consistent across every shot.",
    siteName: "Auteur",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Auteur — The Film Bible Agent",
    description:
      "AI cinema's memory. Grounded in reality. Consistent across every shot.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
