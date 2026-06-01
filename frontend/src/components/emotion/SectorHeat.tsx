// ──────────────────────────────────────────────
// 板块热力榜
// ──────────────────────────────────────────────

"use client";

import React from "react";
import { useEmotion } from "@/lib/emotionStore";

function formatAmount(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}亿`;
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}万`;
  return `${amount}`;
}

export default function SectorHeat() {
  const { snapshot } = useEmotion();
  const sectors = snapshot?.sectorHeat || [];

  if (!snapshot) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 text-center text-slate-500">
        加载中...
      </div>
    );
  }

  if (sectors.length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
        <h2 className="text-sm font-bold text-slate-100 mb-3">🔥 板块热力</h2>
        <div className="text-center text-slate-500 text-xs py-4">今日无板块数据</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
      <h2 className="text-sm font-bold text-slate-100 mb-3">
        🔥 板块热力
        <span className="ml-2 text-xs text-slate-500 font-normal">{sectors.length} 个</span>
      </h2>

      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
        {sectors.map((s, i) => {
          // 热度颜色
          const heatColor = s.count >= 5 ? "text-red-400" :
                           s.count >= 3 ? "text-orange-400" :
                           "text-slate-300";
          const heatBg = s.count >= 5 ? "bg-red-500/10 border-red-500/30" :
                        s.count >= 3 ? "bg-orange-500/10 border-orange-500/30" :
                        "bg-slate-800/30 border-slate-700/30";

          return (
            <div key={s.sector} className={`rounded-lg border p-2.5 ${heatBg} transition-all duration-300`}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-bold ${heatColor}`}>{s.sector}</span>
                  {s.broken > 0 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
                      炸 {s.broken}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-slate-400">
                    涨停 <span className={`font-bold font-mono ${heatColor}`}>{s.count}</span>
                  </span>
                  <span className="text-slate-400">
                    额 <span className="font-mono text-slate-300">{formatAmount(s.totalAmount)}</span>
                  </span>
                </div>
              </div>

              {/* 涨停柱 */}
              <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden mb-1.5">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    s.count >= 5 ? "bg-red-500" : s.count >= 3 ? "bg-orange-500" : "bg-yellow-500"
                  }`}
                  style={{ width: `${Math.min(100, (s.count / 10) * 100)}%` }}
                />
              </div>

              {/* Top 个股 */}
              <div className="flex flex-wrap gap-1">
                {s.stocks.slice(0, 4).map((st) => (
                  <span key={st.code} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/30 text-slate-400">
                    {st.name} <span className="text-red-400">+{st.changePct.toFixed(1)}%</span>
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
