// ──────────────────────────────────────────────
// 情绪周期日历
// ──────────────────────────────────────────────

"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface HistoryEntry {
  date: string;
  metrics: {
    compositeScore: number;
    limitUpCount: number;
    limitDownCount: number;
    brokenRate: number;
    yesterdayLimitUpToday: number;
  };
}

function scoreLabel(score: number): string {
  if (score >= 80) return "高潮";
  if (score >= 65) return "回暖";
  if (score >= 45) return "震荡";
  if (score >= 30) return "分歧";
  return "冰点";
}

function scoreColor(score: number): string {
  if (score >= 80) return "bg-emerald-500/30 border-emerald-500/40 text-emerald-400";
  if (score >= 65) return "bg-green-500/20 border-green-500/30 text-green-400";
  if (score >= 45) return "bg-yellow-500/15 border-yellow-500/30 text-yellow-400";
  if (score >= 30) return "bg-orange-500/15 border-orange-500/30 text-orange-400";
  return "bg-red-500/15 border-red-500/30 text-red-400";
}

function scoreBarColor(score: number): string {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 65) return "bg-green-500";
  if (score >= 45) return "bg-yellow-500";
  if (score >= 30) return "bg-orange-500";
  return "bg-red-500";
}

export default function EmotionCalendar() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const { data } = await axios.get(`${API_BASE}/emotion/history`, { params: { days } });
        setHistory(data.data || []);
      } catch {
        setHistory([]);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [days]);

  if (loading) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
        <h2 className="text-sm font-bold text-slate-100 mb-3">📊 情绪周期</h2>
        <div className="text-center text-slate-500 text-xs py-8">加载中...</div>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
        <h2 className="text-sm font-bold text-slate-100 mb-3">📊 情绪周期</h2>
        <div className="text-center text-slate-500 text-xs py-8">暂无历史数据</div>
      </div>
    );
  }

  // 按日期升序排列
  const sorted = [...history].sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-slate-100">
          📊 情绪周期
          <span className="ml-2 text-xs text-slate-500 font-normal">{sorted.length} 天</span>
        </h2>
        <div className="flex gap-1">
          {[14, 30, 60].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-2 py-0.5 text-xs rounded transition-colors ${
                days === d ? "bg-blue-600/30 text-blue-400" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {d}天
            </button>
          ))}
        </div>
      </div>

      {/* 周期条 */}
      <div className="space-y-1.5 max-h-[350px] overflow-y-auto pr-1">
        {sorted.map((entry) => {
          const score = entry.metrics.compositeScore;
          const label = scoreLabel(score);
          return (
            <div key={entry.date} className="flex items-center gap-2">
              {/* 日期 */}
              <span className="text-[10px] text-slate-500 font-mono w-16 shrink-0">
                {entry.date.slice(5)}
              </span>

              {/* 评分条 */}
              <div className="flex-1 h-5 bg-slate-800/50 rounded overflow-hidden relative">
                <div
                  className={`h-full rounded ${scoreBarColor(score)} transition-all duration-500`}
                  style={{ width: `${score}%` }}
                />
                {/* 分数 */}
                <span className="absolute inset-0 flex items-center px-2 text-[10px] font-mono text-slate-300">
                  {score}分
                </span>
              </div>

              {/* 标签 */}
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0 ${scoreColor(score)}`}>
                {label}
              </span>

              {/* 涨跌停 */}
              <div className="text-[10px] text-slate-500 shrink-0 w-16 text-right font-mono">
                {entry.metrics.limitUpCount}/{entry.metrics.limitDownCount}
              </div>
            </div>
          );
        })}
      </div>

      {/* 图例 */}
      <div className="mt-3 pt-2 border-t border-slate-700/30 flex items-center gap-3 text-[10px] text-slate-500">
        <span>冰点 → 分歧 → 震荡 → 回暖 → 高潮</span>
        <span className="ml-auto">涨跌停: 涨停/跌停</span>
      </div>
    </div>
  );
}
