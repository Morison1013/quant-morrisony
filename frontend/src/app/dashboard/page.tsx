"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import DashboardChart from "@/components/DashboardChart";
import {
  fetchIndices,
  fetchIndexHistory,
  fetchSectorCategories,
  type IndexListItem,
  type SectorCategory,
  type DashboardKLineItem,
} from "@/lib/api";

const FREQUENCIES = [
  { key: "5min", label: "分时" },
  { key: "daily", label: "日K" },
  { key: "weekly", label: "周K" },
  { key: "monthly", label: "月K" },
] as const;

type Frequency = (typeof FREQUENCIES)[number]["key"];

interface IndexCardState {
  code: string;
  name: string;
  data: DashboardKLineItem[];
  freq: Frequency;
  loading: boolean;
}

export default function DashboardPage() {
  const [indices, setIndices] = useState<IndexListItem[]>([]);
  const [cards, setCards] = useState<IndexCardState[]>([]);
  const [categories, setCategories] = useState<SectorCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load index list and sector categories
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        const [idxList, catList] = await Promise.all([
          fetchIndices(),
          fetchSectorCategories(),
        ]);
        setIndices(idxList);
        setCategories(catList.categories);
        // Default: all indices with 分时
        const initialCards: IndexCardState[] = idxList.map((idx) => ({
          code: idx.code,
          name: idx.name,
          data: [],
          freq: "5min",
          loading: true,
        }));
        setCards(initialCards);
      } catch (e: any) {
        setError(e?.message ?? "加载失败");
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // Load data for a single card
  const loadCard = useCallback(async (index: number, code: string, freq: Frequency) => {
    setCards((prev) => prev.map((c, i) => (i === index ? { ...c, loading: true, freq } : c)));
    try {
      const res = await fetchIndexHistory(code, freq, freq === "5min" ? 48 : 120);
      setCards((prev) =>
        prev.map((c, i) => (i === index ? { ...c, data: res.data, loading: false, freq } : c))
      );
    } catch {
      setCards((prev) =>
        prev.map((c, i) => (i === index ? { ...c, data: [], loading: false, freq } : c))
      );
    }
  }, []);

  // Load all cards data
  useEffect(() => {
    if (cards.length === 0) return;
    cards.forEach((card, i) => {
      loadCard(i, card.code, card.freq);
    });
  }, [cards.length]); // only on initial load

  const handleFreqChange = (index: number, freq: Frequency) => {
    loadCard(index, cards[index].code, freq);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 指数看盘面板 */}
        <div>
          <h2 className="text-lg font-bold text-slate-100 mb-4">
            指数看盘
            <span className="ml-2 text-xs text-slate-500 font-normal">点击周期按钮切换</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {cards.map((card, i) => (
              <div key={card.code} className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden">
                {/* 头部：名称 + 周期切换 */}
                <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
                  <span className="text-sm font-semibold text-slate-200">{card.name}</span>
                  <div className="flex gap-1">
                    {FREQUENCIES.map((f) => (
                      <button
                        key={f.key}
                        onClick={() => handleFreqChange(i, f.key)}
                        className={`px-2 py-0.5 text-xs rounded transition-colors font-medium ${
                          card.freq === f.key
                            ? "bg-blue-600/30 text-blue-400"
                            : "text-slate-500 hover:text-slate-300"
                        }`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>
                </div>
                {/* 图表 */}
                <DashboardChart
                  data={card.data}
                  name={card.name}
                  frequency={card.freq}
                  loading={card.loading}
                />
              </div>
            ))}
          </div>
        </div>

        {/* 板块列表 */}
        {categories.length > 0 && (
          <div className="bg-slate-900 rounded-xl border border-slate-700 p-6">
            <h2 className="text-lg font-bold text-slate-100 mb-4">板块指数</h2>

            {categories.map((cat) => (
              <div key={cat.category} className="mb-4 last:mb-0">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  {cat.category}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {cat.sectors.map((s) => (
                    <Link
                      key={s.code}
                      href={`/dashboard/sector/${s.code}`}
                      className="px-3 py-1.5 text-sm rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-300 hover:text-white hover:border-slate-600 hover:bg-slate-800 transition-colors"
                    >
                      {s.name}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl px-4 py-3 text-red-300 text-sm">
            ⚠️ {error}
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 mt-12 py-4 text-center text-xs text-slate-600">
        Quant_Morrisony · A 股量化看盘助手 · 数据源 通达信(pytdx) · 仅供个人复盘参考，不构成投资建议
      </footer>
    </div>
  );
}
