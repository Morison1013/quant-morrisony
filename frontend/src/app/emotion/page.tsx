// ──────────────────────────────────────────────
// 打板情绪监控 — 首页（完整版）
// ──────────────────────────────────────────────

"use client";

import React from "react";
import Header from "@/components/Header";
import { EmotionProvider } from "@/lib/emotionStore";
import {
  EmotionDashboard,
  LimitUpEngine,
  ConsecutiveLadder,
  BrokenReview,
  EmotionCalendar,
  LeaderCompare,
  ReviewTimeIndicator,
  SettingsPanel,
} from "@/components/emotion";

function EmotionMonitorInner() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header />

      {/* 顶部控制栏 */}
      <div className="max-w-[1920px] mx-auto px-4 py-2 flex items-center justify-between border-b border-slate-800/50 bg-slate-900/50">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-slate-100">
            📈 打板情绪监控
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 font-medium">
            日线复盘
          </span>
        </div>
        <div className="flex items-center gap-3">
          <ReviewTimeIndicator />
          <SettingsPanel />
        </div>
      </div>

      {/* 主内容区 */}
      <main className="max-w-[1920px] mx-auto px-4 py-3 space-y-3">
        {/* ── 顶部情绪仪表盘 ── */}
        <EmotionDashboard />

        {/* ── 中间两栏 ── */}
        <div className="grid grid-cols-12 gap-3">
          {/* 左侧：情绪日历 + 涨停强度引擎 + 炸板复盘（6 列） */}
          <div className="col-span-6 flex flex-col gap-3">
            <EmotionCalendar />
            <LimitUpEngine />
            <BrokenReview />
          </div>

          {/* 右侧：龙头对比 + 连板天梯（6 列） */}
          <div className="col-span-6 flex flex-col gap-3">
            <LeaderCompare />
            <ConsecutiveLadder className="flex-1" />
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-800 mt-8 py-4 text-center text-xs text-slate-600">
        Quant_Morrisony · 打板情绪监控 · 数据源 通达信(pytdx) · 每日 12:00 / 14:30 复盘 · 仅供个人复盘参考，不构成投资建议
      </footer>
    </div>
  );
}

export default function EmotionPage() {
  return (
    <EmotionProvider>
      <EmotionMonitorInner />
    </EmotionProvider>
  );
}
