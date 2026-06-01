"use client";

/**
 * RAG 知识库 — 查询输入框
 */

import React, { useState, useRef } from "react";
import { useRAG } from "@/lib/ragStore";

export default function QueryInput() {
  const [input, setInput] = useState("");
  const { query, loading, suggestions } = useRAG();
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    if (!input.trim() || loading) return;
    query(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="px-4 py-3 border-t border-slate-700/50">
      {/* ── 建议问题 ── */}
      {suggestions.length > 0 && !input && (
        <div className="flex flex-wrap gap-1 mb-2">
          {suggestions.slice(0, 3).map((s) => (
            <button
              key={s}
              onClick={() => query(s)}
              className="text-xs px-2 py-1 rounded bg-slate-800/50 text-slate-400 hover:text-slate-300 hover:bg-slate-700/50 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* ── 输入框 ── */}
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入问题，如：均线多头策略是什么..."
          className="flex-1 bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
          disabled={loading}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || loading}
          className={`
            px-3 py-2 rounded-lg text-sm font-medium transition-colors
            ${input.trim() && !loading
              ? "bg-blue-600 hover:bg-blue-500 text-white"
              : "bg-slate-700/50 text-slate-500 cursor-not-allowed"
            }
          `}
        >
          发送
        </button>
      </div>
    </div>
  );
}