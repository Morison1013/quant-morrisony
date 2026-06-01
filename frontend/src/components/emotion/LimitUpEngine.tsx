// ──────────────────────────────────────────────
// 涨停强度引擎 — 主表格（筛选、排序、形态标签、板块标签、分时预览）
// ──────────────────────────────────────────────

"use client";

import React, { useState, useMemo } from "react";
import { useEmotion } from "@/lib/emotionStore";
import MiniChart from "./MiniChart";
import type { LimitUpStock, BoardTag } from "@/lib/emotionTypes";

const TAG_COLORS: Record<string, string> = {
  "首板": "bg-blue-500/20 text-blue-400 border-blue-500/30",
  "二板一字": "bg-purple-500/20 text-purple-400 border-purple-500/30",
  "换手板": "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  "地天板": "bg-orange-500/20 text-orange-400 border-orange-500/30",
  "烂板回封": "bg-red-500/20 text-red-400 border-red-500/30",
  "一字板": "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  "T字板": "bg-pink-500/20 text-pink-400 border-pink-500/30",
  "1板一字": "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
};

const ALL_TAGS: BoardTag[] = ["首板", "二板一字", "换手板", "地天板", "烂板回封", "一字板", "T字板"];

type SortKey = "sealAmount" | "boardCount" | "changePct" | "turnover";

function formatAmount(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}亿`;
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}万`;
  return `${amount}`;
}

export default function LimitUpEngine() {
  const { snapshot } = useEmotion();
  const [filterBoard, setFilterBoard] = useState<"all" | "first" | "multi">("all");
  const [filterTag, setFilterTag] = useState<BoardTag | "all">("all");
  const [filterSector, setFilterSector] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("sealAmount");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [selectedStock, setSelectedStock] = useState<LimitUpStock | null>(null);

  const stocks = snapshot?.limitUpStocks || [];

  // 板块筛选选项
  const sectors = useMemo(() => {
    const s = new Set(stocks.map((s) => s.sector).filter((s) => s !== "—"));
    return ["all", ...Array.from(s).sort()];
  }, [stocks]);

  const filtered = useMemo(() => {
    let result = [...stocks];
    if (filterBoard === "first") result = result.filter((s) => s.boardCount === 1);
    if (filterBoard === "multi") result = result.filter((s) => s.boardCount >= 2);
    if (filterTag !== "all") result = result.filter((s) => s.tag === filterTag);
    if (filterSector !== "all") result = result.filter((s) => s.sector === filterSector);

    result.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      return ((a[sortKey] as number) - (b[sortKey] as number)) * dir;
    });
    return result;
  }, [stocks, filterBoard, filterTag, filterSector, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("desc"); }
  };

  const SortIcon = ({ col }: { col: SortKey }) => (
    <span className="ml-1 text-[10px] text-slate-500">
      {sortKey === col ? (sortDir === "desc" ? "▼" : "▲") : "⇅"}
    </span>
  );

  if (!snapshot) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-8 text-center text-slate-500">
        加载中...
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700/50 overflow-hidden">
      {/* 标题 + 筛选栏 */}
      <div className="px-4 py-3 border-b border-slate-700/50">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold text-slate-100">
            🔥 涨停强度引擎
            <span className="ml-2 text-xs text-slate-500 font-normal">{filtered.length} 只</span>
          </h2>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* 连板筛选 */}
          <div className="flex gap-1">
            {(["all", "first", "multi"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilterBoard(f)}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors font-medium ${
                  filterBoard === f
                    ? "bg-blue-600/30 text-blue-400 border border-blue-500/40"
                    : "bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:border-slate-600"
                }`}
              >
                {f === "all" ? "全部" : f === "first" ? "首板" : "二板+"}
              </button>
            ))}
          </div>

          <span className="text-slate-600 text-xs">|</span>

          {/* 板块筛选 */}
          <select
            value={filterSector}
            onChange={(e) => setFilterSector(e.target.value)}
            className="bg-slate-800/50 text-slate-300 text-xs px-2 py-1 rounded border border-slate-700/50 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {sectors.map((s) => (
              <option key={s} value={s}>{s === "all" ? "全部板块" : s}</option>
            ))}
          </select>

          <span className="text-slate-600 text-xs">|</span>

          {/* 形态标签筛选 */}
          <div className="flex gap-1 flex-wrap">
            <button
              onClick={() => setFilterTag("all")}
              className={`px-2 py-1 text-xs rounded-md transition-colors ${
                filterTag === "all" ? "bg-blue-600/30 text-blue-400 border border-blue-500/40" : "bg-slate-800/50 text-slate-500 border border-slate-700/50"
              }`}
            >
              全部
            </button>
            {ALL_TAGS.map((t) => (
              <button
                key={t}
                onClick={() => setFilterTag(t === filterTag ? "all" : t)}
                className={`px-2 py-1 text-xs rounded-md transition-colors ${
                  filterTag === t ? TAG_COLORS[t] : "bg-slate-800/50 text-slate-500 border border-slate-700/50"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 表格 */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-700/50 text-slate-400 uppercase tracking-wider bg-slate-800/30">
              <th className="px-3 py-2 text-left font-medium">股票</th>
              <th className="px-3 py-2 text-center font-medium cursor-pointer hover:text-slate-200" onClick={() => handleSort("boardCount")}>
                连板<SortIcon col="boardCount" />
              </th>
              <th className="px-3 py-2 text-left font-medium">形态</th>
              <th className="px-3 py-2 text-left font-medium">涨停时间</th>
              <th className="px-3 py-2 text-left font-medium cursor-pointer hover:text-slate-200" onClick={() => handleSort("sealAmount")}>
                成交额<SortIcon col="sealAmount" />
              </th>
              <th className="px-3 py-2 text-center font-medium cursor-pointer hover:text-slate-200" onClick={() => handleSort("changePct")}>
                涨幅<SortIcon col="changePct" />
              </th>
              <th className="px-3 py-2 text-center font-medium">20日走势</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-slate-500">
                  今日无涨停数据（主板）或数据库未刷新
                </td>
              </tr>
            ) : filtered.map((stock) => (
              <tr
                key={stock.code}
                onClick={() => setSelectedStock(stock)}
                className={`border-b border-slate-800/30 cursor-pointer transition-colors hover:bg-slate-800/40 ${
                  selectedStock?.code === stock.code ? "bg-blue-600/10" : ""
                }`}
              >
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium text-slate-100">{stock.name}</span>
                    {stock.sector !== "—" && (
                      <span className="px-1.5 py-0.5 text-[10px] rounded bg-slate-700/50 text-slate-400 border border-slate-600/30">
                        {stock.sector}
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono">{stock.code}</div>
                </td>
                <td className="px-3 py-2.5 text-center">
                  <span className={`font-black font-mono text-sm ${
                    stock.boardCount >= 4 ? "text-red-400" :
                    stock.boardCount >= 3 ? "text-orange-400" :
                    stock.boardCount >= 2 ? "text-yellow-400" : "text-slate-300"
                  }`}>
                    {stock.boardCount}板
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <span className={`px-1.5 py-0.5 text-[10px] rounded border font-medium ${TAG_COLORS[stock.tag] || "bg-slate-700 text-slate-400"}`}>
                    {stock.tag}
                  </span>
                </td>
                <td className="px-3 py-2.5 font-mono text-slate-400 text-[10px]">
                  {stock.firstLimitTime === "N/A" ? "日线数据" : stock.firstLimitTime}
                </td>
                <td className="px-3 py-2.5 font-mono text-slate-300">
                  {formatAmount(stock.sealAmount)}
                </td>
                <td className="px-3 py-2.5 text-center font-mono text-red-400">
                  +{stock.changePct.toFixed(1)}%
                </td>
                <td className="px-3 py-2.5">
                  <MiniChart data={stock.intraData} width={80} height={24} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
