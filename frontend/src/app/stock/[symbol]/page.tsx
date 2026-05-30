"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import Header from "@/components/Header";
import KLineChart from "@/components/KLineChart";
import SummaryCard from "@/components/SummaryCard";
import { fetchHistory, fetchSummary, type KLineItem, type SummaryResponse } from "@/lib/api";

export default function StockDetailPage() {
  const params = useParams();
  const symbol = (params.symbol as string) || "";

  const [history, setHistory] = useState<KLineItem[]>([]);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;

    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [h, s] = await Promise.all([fetchHistory(symbol), fetchSummary(symbol)]);
        setHistory(h.data);
        setSummary(s);
      } catch (e: any) {
        setError(e?.response?.data?.detail ?? e?.message ?? "数据加载失败");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [symbol]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 返回按钮 */}
        <div className="flex items-center gap-3">
          <Link
            href="/scanner"
            className="px-3 py-1.5 text-sm rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 transition-colors"
          >
            ← 返回扫描
          </Link>
          <Link
            href="/"
            className="px-3 py-1.5 text-sm rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 transition-colors"
          >
            股票查询
          </Link>
          <span className="text-lg font-bold text-slate-100 ml-2">
            {summary?.symbol || symbol}
          </span>
          {summary && (
            <span className="text-xs text-slate-500">
              · {summary.latest_date} · 收盘 {summary.latest_close}
            </span>
          )}
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl px-4 py-3 text-red-300 text-sm">
            ⚠️ {error} — 请确认后端服务已启动（localhost:8000）
          </div>
        )}

        {/* K 线图 */}
        <KLineChart data={history} loading={loading} />

        {/* 策略复盘摘要 */}
        <SummaryCard summary={summary} loading={loading} />
      </main>

      <footer className="border-t border-slate-800 mt-12 py-4 text-center text-xs text-slate-600">
        Quant_Morrisony · A 股量化看盘助手 · 数据源 通达信(pytdx) · 仅供个人复盘参考，不构成投资建议
      </footer>
    </div>
  );
}
