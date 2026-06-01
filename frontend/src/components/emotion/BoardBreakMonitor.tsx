// ──────────────────────────────────────────────
// 炸板与回封监控面板
// ──────────────────────────────────────────────

"use client";

import React, { useMemo } from "react";
import { useEmotion } from "@/lib/emotionStore";
import type { BrokenBoard } from "@/lib/emotionTypes";

function formatAmount(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}亿`;
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}万`;
  return `${amount}`;
}

/* ── 炸板池 ── */
function BrokenPool({ boards }: { boards: BrokenBoard[] }) {
  if (boards.length === 0) {
    return (
      <div className="text-center py-6 text-slate-500 text-xs">
        今日无炸板数据（日线推算）
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-red-400">
          💥 炸板池
          <span className="ml-1 text-slate-500 font-normal">({boards.length}只)</span>
        </h3>
        <span className="text-[10px] text-slate-500">按成交额排序</span>
      </div>

      <div className="space-y-1.5 max-h-[280px] overflow-y-auto pr-1">
        {boards.map((b) => {
          const dropFromHigh = b.highPct - b.currentPct;
          return (
            <div
              key={b.code}
              className={`rounded-lg px-3 py-2 border transition-all duration-300 ${
                b.status === "回封"
                  ? "bg-emerald-500/5 border-emerald-500/30"
                  : "bg-slate-800/30 border-slate-700/30 hover:border-slate-600"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-100">{b.name}</span>
                  <span className="text-[10px] text-slate-500 font-mono">{b.code}</span>
                  <span className="text-[10px] text-slate-500">{b.boardCount}板</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500">
                    涨幅 <span className={`font-mono ${b.currentPct > 0 ? "text-red-400" : "text-green-400"}`}>
                      {b.currentPct > 0 ? "+" : ""}{b.currentPct.toFixed(1)}%
                    </span>
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between mt-1 text-[10px] text-slate-500">
                <div className="flex items-center gap-3">
                  <span>成交额 {formatAmount(b.brokenAmount)}</span>
                  {dropFromHigh > 0 && (
                    <span className="text-orange-400">回落 {dropFromHigh.toFixed(1)}%</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── 回封观察列表 ── */
function ResealWatch({ boards }: { boards: BrokenBoard[] }) {
  const watchList = useMemo(
    () => boards.filter((b) => b.currentPct > 5 && b.highPct - b.currentPct < 3),
    [boards]
  );

  if (watchList.length === 0) {
    return (
      <div className="text-center py-4 text-slate-500 text-xs">
        暂无回封观察标的
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold text-emerald-400">
          🔄 回封观察
          <span className="ml-1 text-slate-500 font-normal">({watchList.length}只)</span>
        </h3>
        <span className="text-[10px] text-slate-500">涨幅 &gt; 5% 且回落 &lt; 3%</span>
      </div>

      <div className="space-y-1.5">
        {watchList.map((b) => {
          const distToLimit = 10 - b.currentPct;
          return (
            <div
              key={b.code}
              className="rounded-lg px-3 py-2 border border-emerald-500/20 bg-emerald-500/5 hover:border-emerald-500/40 transition-all duration-300"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-100">{b.name}</span>
                  <span className="text-[10px] text-slate-500 font-mono">{b.code}</span>
                </div>
                <div className="text-xs font-mono text-red-400">
                  +{b.currentPct.toFixed(1)}%
                </div>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px]">
                <div className="flex items-center gap-3 text-slate-500">
                  <span>距涨停 {distToLimit.toFixed(1)}%</span>
                  <span>成交额 {formatAmount(b.brokenAmount)}</span>
                </div>
                {distToLimit < 2 && (
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-yellow-500/20 text-yellow-400 font-medium animate-pulse">
                    ⚡ 即将回封！
                  </span>
                )}
              </div>
              <div className="mt-1.5 h-1 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-yellow-400 rounded-full transition-all duration-500"
                  style={{ width: `${((10 - distToLimit) / 10) * 100}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function BoardBreakMonitor() {
  const { snapshot } = useEmotion();

  const brokenBoards = snapshot?.brokenBoards || [];

  if (!snapshot) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 text-center text-slate-500">
        加载中...
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 space-y-4">
      <h2 className="text-sm font-bold text-slate-100">
        💔 炸板与回封监控
      </h2>
      <BrokenPool boards={brokenBoards} />
      <div className="border-t border-slate-700/30 pt-3">
        <ResealWatch boards={brokenBoards} />
      </div>
    </div>
  );
}
