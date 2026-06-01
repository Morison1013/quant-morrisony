// ──────────────────────────────────────────────
// 核心情绪仪表盘 — 顶部 5 个指标卡片
// ──────────────────────────────────────────────

"use client";

import React, { useState, useMemo } from "react";
import { useEmotion } from "@/lib/emotionStore";
import type { SentimentMetrics } from "@/lib/emotionTypes";

const LEVEL_OPTIONS = ["1进2", "2进3", "3进4", "4进5", "5进6"] as const;

/* ── 昨日涨停今日表现卡片 ── */
function YesterdayLimitUpCard({ metrics }: { metrics: SentimentMetrics }) {
  const val = metrics.yesterdayLimitUpToday;
  const isPositive = val > 0;
  const color = val > 3 ? "bg-emerald-500/20 border-emerald-400/50 shadow-lg shadow-emerald-500/20" :
                val < -2 ? "bg-red-500/20 border-red-400/50 shadow-lg shadow-red-500/20 animate-pulse" :
                isPositive ? "bg-blue-500/10 border-blue-500/30" :
                "bg-slate-800/50 border-slate-700/50";
  const textColor = val > 3 ? "text-emerald-400" :
                    val < -2 ? "text-red-400" :
                    isPositive ? "text-blue-400" : "text-slate-300";
  const label = val > 3 ? "情绪极好" :
                val < -2 ? "亏钱效应极强，暂停打板" :
                val > 0 ? "溢价正常" : "溢价偏低";

  return (
    <div className={`rounded-xl border p-4 ${color} transition-all duration-500`}>
      <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">昨日涨停今日表现</div>
      <div className={`text-2xl font-black font-mono transition-all duration-300 ${textColor}`}>
        {val > 0 ? "+" : ""}{val.toFixed(1)}%
      </div>
      <div className={`text-xs mt-1 font-medium ${textColor}`}>{label}</div>
    </div>
  );
}

/* ── 炸板率卡片 ── */
function BrokenRateCard({ metrics }: { metrics: SentimentMetrics }) {
  const val = metrics.brokenRate;
  const color = val < 25 ? "bg-emerald-500/10 border-emerald-400/30" :
                val > 40 ? "bg-red-500/20 border-red-400/50 animate-pulse" :
                "bg-yellow-500/10 border-yellow-500/30";
  const textColor = val < 25 ? "text-emerald-400" :
                    val > 40 ? "text-red-400" : "text-yellow-400";
  const label = val < 25 ? "封板意愿强" :
                val > 40 ? "市场分歧巨大，风险高" : "正常范围";

  return (
    <div className={`rounded-xl border p-4 ${color} transition-all duration-500`}>
      <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">炸板率</div>
      <div className={`text-2xl font-black font-mono transition-all duration-300 ${textColor}`}>
        {val.toFixed(0)}%
      </div>
      <div className={`text-xs mt-1 font-medium ${textColor}`}>{label}</div>
    </div>
  );
}

/* ── 涨停/跌停家数卡片 ── */
function UpDownCard({ metrics }: { metrics: SentimentMetrics }) {
  const { limitUpCount, limitDownCount } = metrics;
  const isDanger = limitDownCount > 10;

  return (
    <div className="rounded-xl border p-4 bg-slate-800/50 border-slate-700/50 transition-all duration-500">
      <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">涨停 / 跌停</div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-black font-mono text-red-400 transition-all duration-300">
          {limitUpCount}
        </span>
        <span className="text-slate-600 text-lg font-bold">|</span>
        <span className={`text-3xl font-black font-mono transition-all duration-300 ${
          isDanger ? "text-green-400 animate-pulse" : "text-green-400"
        }`}>
          {limitDownCount}
        </span>
      </div>
      {isDanger && (
        <div className="text-xs mt-1 text-red-400 font-medium animate-pulse">
          ⚠ 跌停家数过多
        </div>
      )}
    </div>
  );
}

/* ── 连板晋级率卡片 ── */
function PromotionRateCard({ metrics }: { metrics: SentimentMetrics }) {
  const allRates = metrics.promotionRates || {};
  const defaultRate = metrics.promotionRate;
  const [level, setLevel] = useState(defaultRate.level);

  const selectedRate = allRates[level] || defaultRate;

  return (
    <div className="rounded-xl border p-4 bg-slate-800/50 border-slate-700/50 transition-all duration-500">
      <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">连板晋级率</div>
      <div className="relative">
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="appearance-none bg-slate-700/50 text-slate-200 text-xs px-2 py-0.5 rounded border border-slate-600/50 cursor-pointer focus:outline-none focus:ring-1 focus:ring-blue-500 pr-6"
        >
          {Object.keys(allRates).length > 0
            ? Object.keys(allRates).filter(k => k !== "default").map((l) => (
                <option key={l} value={l}>{l}</option>
              ))
            : LEVEL_OPTIONS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))
          }
        </select>
      </div>
      <div className="text-2xl font-black font-mono text-blue-400 mt-2 transition-all duration-300">
        {selectedRate.rate}%
      </div>
      <div className="text-xs text-slate-400 mt-0.5">
        {selectedRate.success}/{selectedRate.total}
      </div>
    </div>
  );
}

/* ── 综合评分圆形进度条 ── */
function CompositeScoreCard({ score }: { score: number }) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const color = score >= 70 ? "#10b981" :
                score >= 50 ? "#f59e0b" :
                score >= 40 ? "#f97316" : "#ef4444";
  const label = score >= 70 ? "可操作区间" :
                score >= 50 ? "谨慎操作" :
                score >= 40 ? "轻仓试探" : "建议空仓";

  return (
    <div className="rounded-xl border p-4 bg-slate-800/50 border-slate-700/50 flex flex-col items-center justify-center transition-all duration-500">
      <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">情绪综合评分</div>
      <div className="relative w-20 h-20">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r={radius} fill="none" stroke="#1e293b" strokeWidth="6" />
          <circle
            cx="40" cy="40" r={radius} fill="none" stroke={color} strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-700 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-black" style={{ color }}>{score}</span>
          <span className="text-[9px] text-slate-500 -mt-1">分</span>
        </div>
      </div>
      <div className="text-xs mt-1 font-medium" style={{ color }}>{label}</div>
    </div>
  );
}

export default function EmotionDashboard() {
  const { snapshot, loading } = useEmotion();

  if (loading || !snapshot) {
    return (
      <div className="grid grid-cols-5 gap-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="rounded-xl border border-slate-700/50 bg-slate-900 p-4 animate-pulse">
            <div className="h-3 bg-slate-700 rounded w-20 mb-2" />
            <div className="h-8 bg-slate-700 rounded w-16 mb-1" />
            <div className="h-3 bg-slate-700 rounded w-24" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-5 gap-3">
      <YesterdayLimitUpCard metrics={snapshot.metrics} />
      <BrokenRateCard metrics={snapshot.metrics} />
      <UpDownCard metrics={snapshot.metrics} />
      <PromotionRateCard metrics={snapshot.metrics} />
      <CompositeScoreCard score={snapshot.metrics.compositeScore} />
    </div>
  );
}
