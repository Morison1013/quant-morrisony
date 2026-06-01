"use client";

/**
 * RAG 知识库 — 单条消息组件
 */

import React, { useState } from "react";
import type { ChatMessage } from "@/lib/ragTypes";

export default function ChatMessage({ message }: { message: ChatMessage }) {
  const [showDocs, setShowDocs] = useState(false);
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "order-1" : ""}`}>
        {/* ── 消息气泡 ── */}
        <div
          className={`
            rounded-lg px-3 py-2 text-sm whitespace-pre-wrap
            ${isUser
              ? "bg-blue-600/20 border border-blue-500/30 text-blue-100"
              : "bg-slate-800/50 border border-slate-700/50 text-slate-200"
            }
          `}
        >
          {message.content}
        </div>

        {/* ── 附加信息（助手消息）── */}
        {!isUser && message.retrieved_docs && message.retrieved_docs.length > 0 && (
          <div className="mt-2 flex items-center gap-2 text-xs">
            <button
              onClick={() => setShowDocs(!showDocs)}
              className="text-slate-400 hover:text-slate-300 underline"
            >
              {showDocs
                ? "隐藏参考"
                : `查看参考 (${message.retrieved_docs.length})`}
            </button>
            {message.elapsed_ms && (
              <span className="text-slate-600">{message.elapsed_ms}ms</span>
            )}
            {message.confidence !== undefined && (
              <span
                className={`px-1.5 py-0.5 rounded ${
                  message.confidence > 0.7
                    ? "bg-emerald-500/20 text-emerald-400"
                  : message.confidence > 0.5
                    ? "bg-yellow-500/20 text-yellow-400"
                    : "bg-red-500/20 text-red-400"
                }`}
              >
                {Math.round(message.confidence * 100)}%
              </span>
            )}
          </div>
        )}

        {/* ── 参考文档展开 ── */}
        {showDocs && message.retrieved_docs && (
          <div className="mt-2 space-y-1.5">
            {message.retrieved_docs.map((doc) => (
              <div
                key={doc.doc_id}
                className="bg-slate-800/30 rounded p-2 border border-slate-700/30"
              >
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-slate-300">{doc.title}</span>
                  <span className="text-slate-500">{doc.category}</span>
                  <span className="text-emerald-400">
                    {Math.round(doc.score * 100)}%
                  </span>
                </div>
                <div className="text-xs text-slate-400 mt-1 line-clamp-2">
                  {doc.content}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}