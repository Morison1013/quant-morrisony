// ──────────────────────────────────────────────
// 龙头对比面板
// ──────────────────────────────────────────────

"use client";

import React, { useState } from "react";
import { useEmotion } from "@/lib/emotionStore";

function formatAmount(amount: number): string {
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(1)}亿`;
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(0)}万`;
  return `${amount}`;
}

const TAG_COLORS: Record<string, string> = {
  "首板": "bg-blue-500/20 text-blue-400",
  "换手板": "bg-yellow-500/20 text-yellow-400",
  "一字板": "bg-cyan-500/20 text-cyan-400",
  "T字板": "bg-pink-500/20 text-pink-400",
  "烂板回封": "bg-red-500/20 text-red-400",
};

export default function LeaderCompare() {
  const { snapshot } = useEmotion();
  const leaders = snapshot?.leaders || [];
  const [customCodes, setCustomCodes] = useState("");

  if (!snapshot) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 text-center text-slate-500">
        加载中...
      </div>
    );
  }

  if (leaders.length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
        <h2 className="text-sm font-bold text-slate-100 mb-3">👑 龙头对比</h2>
        <div className="text-center text-slate-500 text-xs py-4">今日无龙头股数据</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
      <h2 className="text-sm font-bold text-slate-100 mb-3">
        👑 龙头对比
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-700/50 text-slate-400 bg-slate-800/30">
              <th className="px-3 py-2 text-left font-medium">指标</th>
              {leaders.map((l) => (
                <th key={l.code} className="px-3 py-2 text-center font-medium">
                  <div className="font-bold text-slate-200">{l.name}</div>
                  <div className="text-[10px] text-slate-500 font-mono">{l.code}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* 连板数 */}
            <tr className="border-b border-slate-800/20">
              <td className="px-3 py-2 text-slate-400">连板数</td>
              {leaders.map((l) => (
                <td key={l.code} className="px-3 py-2 text-center">
                  <span className={`font-black font-mono text-base ${
                    l.isHighest ? "text-yellow-400" :
                    l.boardCount >= 4 ? "text-red-400" :
                    l.boardCount >= 3 ? "text-orange-400" : "text-slate-300"
                  }`}>
                    {l.boardCount}板
                  </span>
                  {l.isHighest && <span className="ml-1 text-[10px]">👑</span>}
                </td>
              ))}
            </tr>

            {/* 涨跌幅 */}
            <tr className="border-b border-slate-800/20">
              <td className="px-3 py-2 text-slate-400">今日涨幅</td>
              {leaders.map((l) => (
                <td key={l.code} className="px-3 py-2 text-center font-mono text-red-400">
                  +{l.changePct.toFixed(1)}%
                </td>
              ))}
            </tr>

            {/* 形态 */}
            <tr className="border-b border-slate-800/20">
              <td className="px-3 py-2 text-slate-400">形态</td>
              {leaders.map((l) => (
                <td key={l.code} className="px-3 py-2 text-center">
                  <span className={`px-1.5 py-0.5 text-[10px] rounded ${TAG_COLORS[l.tag] || "bg-slate-700 text-slate-400"}`}>
                    {l.tag}
                  </span>
                </td>
              ))}
            </tr>

            {/* 成交额 */}
            <tr className="border-b border-slate-800/20">
              <td className="px-3 py-2 text-slate-400">成交额</td>
              {leaders.map((l) => (
                <td key={l.code} className="px-3 py-2 text-center font-mono text-slate-300">
                  {formatAmount(l.sealAmount)}
                </td>
              ))}
            </tr>

            {/* 换手率 */}
            <tr>
              <td className="px-3 py-2 text-slate-400">换手率</td>
              {leaders.map((l) => (
                <td key={l.code} className="px-3 py-2 text-center font-mono text-slate-300">
                  {l.turnover.toFixed(1)}%
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
