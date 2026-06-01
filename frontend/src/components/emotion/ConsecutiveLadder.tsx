// ──────────────────────────────────────────────
// 连板天梯 + 情绪标杆
// ──────────────────────────────────────────────

"use client";

import React from "react";
import { useEmotion } from "@/lib/emotionStore";
import type { ConsecutiveBoard } from "@/lib/emotionTypes";

/* ── 情绪标杆（最高标卡片） ── */
function HighestBoardCard({ board }: { board: ConsecutiveBoard }) {
  return (
    <div className="bg-gradient-to-br from-yellow-500/10 via-orange-500/5 to-slate-900 rounded-xl border border-yellow-500/30 p-4 relative overflow-hidden">
      <div className="absolute top-2 right-2 text-2xl opacity-30">👑</div>

      <div className="flex items-center gap-3">
        <div className="bg-yellow-500/20 rounded-lg px-3 py-1 border border-yellow-500/30">
          <span className="text-yellow-400 text-[10px] uppercase tracking-wider font-bold">最高标</span>
          <div className="text-3xl font-black text-yellow-400 font-mono">{board.boardCount}板</div>
        </div>

        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-slate-100">{board.name}</span>
            <span className="text-xs text-slate-500 font-mono">{board.code}</span>
          </div>
          <div className="flex items-center gap-4 mt-1 text-xs">
            <span className="text-red-400 font-mono font-medium">+{board.changePct.toFixed(1)}%</span>
            <span className="text-slate-400">
              成交额 <span className="text-orange-400 font-mono">{(board.sealAmount / 1e8).toFixed(2)}亿</span>
            </span>
            <span className="text-slate-400">
              形态 <span className="text-cyan-400 font-medium">{board.tag}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── 梯队链条 ── */
function BoardLevelRow({ level, boards }: { level: number; boards: ConsecutiveBoard[] }) {
  const indentMap: Record<number, string> = {
    5: "ml-0",
    4: "ml-8",
    3: "ml-16",
    2: "ml-24",
    1: "ml-32",
  };

  return (
    <div className={`${indentMap[level] || "ml-32"} mb-2`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold w-8">
          {level}板
        </span>
        <div className="flex-1 h-px bg-slate-700/50" />
        <span className="text-[10px] text-slate-600">{boards.length} 只</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {boards.map((b) => {
          const isBroken = b.status !== "封死";
          return (
            <div
              key={b.code}
              className={`rounded-lg px-3 py-2 border transition-all duration-300 cursor-pointer min-w-[110px] ${
                isBroken
                  ? "bg-slate-800/30 border-slate-700/30 opacity-60"
                  : "bg-slate-800/50 border-slate-600/50 hover:border-blue-500/50 hover:bg-blue-500/5"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span className={`text-sm font-bold ${
                  isBroken ? "text-slate-500 line-through" : "text-slate-100"
                }`}>
                  {b.name}
                </span>
                {isBroken && (
                  <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/20 text-red-400 font-medium">
                    断板
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500">
                <span className={`font-mono ${
                  b.changePct > 0 ? "text-red-400" : "text-green-400"
                }`}>
                  {b.changePct > 0 ? "+" : ""}{b.changePct.toFixed(1)}%
                </span>
                <span className="font-mono">{(b.sealAmount / 1e4).toFixed(0)}万</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function ConsecutiveLadder() {
  const { snapshot } = useEmotion();

  const boards = snapshot?.consecutiveBoards || [];
  const highest = boards.find((b) => b.isHighest);
  const rest = boards.filter((b) => !b.isHighest);

  const levels = Array.from({ length: 6 }, (_, i) => 6 - i)
    .map((l) => ({
      level: l,
      boards: rest.filter((b) => b.boardCount === l),
    }))
    .filter((g) => g.boards.length > 0);

  if (!snapshot) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4 text-center text-slate-500">
        加载中...
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700/50 p-4">
      <h2 className="text-sm font-bold text-slate-100 mb-3">
        🏔️ 连板天梯
        <span className="ml-2 text-xs text-slate-500 font-normal">
          {boards.length} 只
        </span>
      </h2>

      {/* 最高标 */}
      {highest && <HighestBoardCard board={highest} />}

      {/* 梯队 */}
      <div className="mt-4 space-y-1">
        {levels.map(({ level, boards: levelBoards }) => (
          <BoardLevelRow key={level} level={level} boards={levelBoards} />
        ))}
      </div>

      {levels.length === 0 && (
        <div className="text-center py-8 text-slate-500 text-xs">
          今日无连板数据
        </div>
      )}
    </div>
  );
}
