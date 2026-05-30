"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import Header from "@/components/Header";
import DashboardChart from "@/components/DashboardChart";
import {
  fetchSectorHistory,
  fetchSectorCategories,
  type DashboardKLineItem,
} from "@/lib/api";

const FREQUENCIES = [
  { key: "5min", label: "分时" },
  { key: "daily", label: "日K" },
  { key: "weekly", label: "周K" },
  { key: "monthly", label: "月K" },
] as const;

type Frequency = (typeof FREQUENCIES)[number]["key"];

export default function SectorDetailPage() {
  const params = useParams();
  const symbol = (params.symbol as string) || "";

  const [data, setData] = useState<DashboardKLineItem[]>([]);
  const [frequency, setFrequency] = useState<Frequency>("5min");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState(symbol);
  const [allSectors, setAllSectors] = useState<{ code: string; name: string }[]>([]);

  // Load sector categories to get name
  useEffect(() => {
    fetchSectorCategories().then((res) => {
      const all = res.categories.flatMap((c) => c.sectors);
      setAllSectors(all);
      const sector = all.find((s) => s.code === symbol);
      if (sector) setName(sector.name);
    });
  }, [symbol]);

  // Load sector data
  useEffect(() => {
    if (!symbol) return;

    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const limit = frequency === "5min" ? 48 : 120;
        const res = await fetchSectorHistory(symbol, frequency, limit);
        setData(res.data);
        setName(res.name);
      } catch (e: any) {
        setError(e?.message ?? "数据加载失败");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [symbol, frequency]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 返回 + 标题 */}
        <div className="flex items-center gap-3 flex-wrap">
          <Link
            href="/dashboard"
            className="px-3 py-1.5 text-sm rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 transition-colors"
          >
            ← 返回看板
          </Link>
          <span className="text-lg font-bold text-slate-100">{name}</span>
          <span className="text-xs text-slate-500 font-mono">{symbol}</span>

          {/* 周期选择 */}
          <div className="flex gap-1 ml-auto">
            {FREQUENCIES.map((f) => (
              <button
                key={f.key}
                onClick={() => setFrequency(f.key)}
                className={`px-3 py-1 text-xs rounded-lg border transition-colors font-medium ${
                  frequency === f.key
                    ? "bg-blue-600/20 border-blue-500/50 text-blue-400"
                    : "bg-slate-800/50 border-slate-700/50 text-slate-400 hover:text-slate-200 hover:border-slate-600"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* 其他板块快捷链接 */}
        {allSectors.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {allSectors
              .filter((s) => s.code !== symbol)
              .slice(0, 20)
              .map((s) => (
                <Link
                  key={s.code}
                  href={`/dashboard/sector/${s.code}`}
                  className="px-2 py-1 text-xs rounded-md bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white hover:border-slate-600 transition-colors"
                >
                  {s.name}
                </Link>
              ))}
          </div>
        )}

        {error && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl px-4 py-3 text-red-300 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* 图表 */}
        <DashboardChart data={data} name={name} frequency={frequency} loading={loading} />
      </main>

      <footer className="border-t border-slate-800 mt-12 py-4 text-center text-xs text-slate-600">
        Quant_Morrisony · A 股量化看盘助手 · 数据源 通达信(pytdx) · 仅供个人复盘参考，不构成投资建议
      </footer>
    </div>
  );
}
