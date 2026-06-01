"use client";

/**
 * RAG 知识库 — 聊天面板
 */

import React, { useRef, useEffect } from "react";
import { useRAG } from "@/lib/ragStore";
import ChatMessage from "./ChatMessage";
import QueryInput from "./QueryInput";

export default function ChatPanel() {
  const { messages, loading, isOpen } = useRAG();
  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed bottom-24 right-6 z-50 w-[420px] max-h-[600px] rounded-xl border border-slate-700 bg-slate-900/95 backdrop-blur shadow-2xl flex flex-col"
    >
      {/* ── 头部 ── */}
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-slate-100">量化知识库</span>
          <span
            className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
          >
            RAG
          </span>
        </div>
        <span className="text-xs text-slate-500">基于 DeepSeek</span>
      </div>

      {/* ── 消息区 ── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[300px] max-h-[400px]"
      >
        {messages.length === 0 ? (
          <div className="text-center text-slate-500 py-8">
            <div className="text-sm">欢迎咨询量化策略相关问题</div>
            <div className="text-xs mt-2 text-slate-600">
              支持：策略说明、概念解释、使用指南
            </div>
          </div>
        ) : (
          messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
        )}
        {loading && (
          <div className="flex items-center gap-2 text-slate-400 text-sm">
            <div
              className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"
            />
            正在思考...
          </div>
        )}
      </div>

      {/* ── 输入区 ── */}
      <QueryInput />
    </div>
  );
}