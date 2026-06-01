"use client";

/**
 * RAG 知识库 — 悬浮问答按钮
 */

import React from "react";
import { useRAG } from "@/lib/ragStore";

export default function FloatingChatButton() {
  const { isOpen, setOpen } = useRAG();

  return (
    <button
      onClick={() => setOpen(!isOpen)}
      className={`
        fixed bottom-6 right-6 z-50
        w-14 h-14 rounded-full
        flex items-center justify-center
        transition-all duration-300
        shadow-lg hover:shadow-xl
        ${isOpen
          ? "bg-slate-700 hover:bg-slate-600"
          : "bg-blue-600 hover:bg-blue-500 animate-pulse"
        }
      `}
      title="知识库问答"
      aria-label="打开知识库问答"
    >
      {isOpen ? (
        <svg
          className="w-6 h-6 text-slate-200"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      ) : (
        <svg
          className="w-6 h-6 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      )}
    </button>
  );
}