import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { RAGProvider } from "@/lib/ragStore";
import { FloatingChatButton, ChatPanel } from "@/components/rag";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Quant_Morrisony — A 股量化看盘助手",
  description: "AkShare 数据 + Pandas 策略计算 + FastAPI 原子接口 + Next.js 可视化看板",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`dark ${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-slate-950">
        <RAGProvider>
          {children}
          <FloatingChatButton />
          <ChatPanel />
        </RAGProvider>
      </body>
    </html>
  );
}
