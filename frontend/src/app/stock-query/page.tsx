"use client";

import React, { useState, useEffect } from "react";
import Header from "@/components/Header";
import KLineChart from "@/components/KLineChart";
import SummaryCard from "@/components/SummaryCard";
import { fetchHistory, fetchSummary, type KLineItem, type SummaryResponse } from "@/lib/api";

export default function StockQueryPage() {
  const [symbol, setSymbol] = useState("600519");
  const [history, setHistory] = useState<KLineItem[]>([]);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (code: string) => {
    setLoading(true);
    setError(null);
    try {
      const [h, s] = await Promise.all([fetchHistory(code), fetchSummary(code)]);
      setHistory(h.data);
      setSummary(s);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "数据加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(symbol);
  }, [symbol]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const input = form.elements.namedItem("symbol") as HTMLInputElement;
    const code = input.value.trim();
    if (code) {
      setSymbol(code);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 股票代码输入 */}
        <div className="bg-slate-900 rounded-xl border border-slate-700 p-4">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-300">股票代码：</label>
            <input
              name="symbol"
              type="text"
              placeholder="600519"
              defaultValue={symbol}
              className="w-44 px-3 py-1.5 text-sm rounded-lg bg-slate-800 border border-slate-600 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
            />
            <button
              type="submit"
              className="px-6 py-1.5 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 transition-colors font-medium"
            >
              查询
            </button>
          </form>
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
