// ──────────────────────────────────────────────
// 炸板复盘排行
// ──────────────────────────────────────────────

"use client";

import React from "react";
import { useEmotion } from "@/lib/emotionStore";

function formatAmount(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}亿`;
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}万`;
  return `${amount}`;
}

export default function BrokenReview() {
  const { snapshot } = useEmotion();
  const review = snapshot?.brokenReview || [];

  if (!snapshot) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 text-center text-slate-500">
        加载中...
      </div>
    );
  }

  if (review.length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
        <h2 className="text-sm font-bold text-slate-100 mb-3">💔 炸板复盘</h2>
        <div className="text-center text-slate-500 text-xs py-4">今日无炸板个股</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700/50 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700/50">
        <h2 className="text-sm font-bold text-slate-100">
          💔 炸板复盘
          <span className="ml-2 text-xs text-slate-500 font-normal">{review.length} 只</span>
        </h2>
        <p className="text-[10px] text-slate-500 mt-0.5">昨日涨停但今天回落的股票（按回撤幅度排序）</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-700/50 text-slate-400 bg-slate-800/30">
              <th className="px-3 py-2 text-left font-medium">股票</th>
              <th className="px-3 py-2 text-center font-medium">开涨</th>
              <th className="px-3 py-2 text-center font-medium">最高</th>
              <th className="px-3 py-2 text-center font-medium">现价</th>
              <th className="px-3 py-2 text-center font-medium">回撤</th>
              <th className="px-3 py-2 text-center font-medium">成交额</th>
            </tr>
          </thead>
          <tbody>
            {review.map((r) => (
              <tr key={r.code} className="border-b border-slate-800/30 hover:bg-slate-800/30 transition-colors">
                <td className="px-3 py-2">
                  <div className="font-medium text-slate-100">{r.name}</div>
                  <div className="text-[10px] text-slate-500 font-mono">{r.code}</div>
                </td>
                <td className="px-3 py-2 text-center font-mono text-red-400">
                  +{r.openPct.toFixed(1)}%
                </td>
                <td className="px-3 py-2 text-center font-mono text-orange-400">
                  +{r.highPct.toFixed(1)}%
                </td>
                <td className="px-3 py-2 text-center font-mono">
                  <span className={r.currentPct > 0 ? "text-red-400" : "text-green-400"}>
                    {r.currentPct > 0 ? "+" : ""}{r.currentPct.toFixed(1)}%
                  </span>
                </td>
                <td className="px-3 py-2 text-center">
                  <span className="font-mono font-bold text-red-400">
                    -{r.pullback.toFixed(1)}%
                  </span>
                </td>
                <td className="px-3 py-2 text-center font-mono text-slate-300">
                  {formatAmount(r.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
