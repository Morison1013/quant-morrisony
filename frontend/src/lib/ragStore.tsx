"use client";

/**
 * RAG 知识库 — 全局状态管理
 *
 * 参考 emotionStore.tsx 的 Context + hooks 模式
 */

import React, { createContext, useContext, useState, useCallback } from "react";
import type { ChatMessage, RAGQueryResponse, QueryCategory } from "./ragTypes";
import { queryKnowledge } from "./ragApi";

interface RAGContextType {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  session_id: string;
  isOpen: boolean;
  suggestions: string[];
  query: (text: string, category?: QueryCategory) => Promise<void>;
  setOpen: (open: boolean) => void;
  clearMessages: () => void;
}

const RAGContext = createContext<RAGContextType | null>(null);

export function useRAG() {
  const ctx = useContext(RAGContext);
  if (!ctx) throw new Error("useRAG must be used within RAGProvider");
  return ctx;
}

// 默认建议问题
const DEFAULT_SUGGESTIONS = [
  "均线多头策略怎么用？",
  "MACD金叉信号的条件是什么？",
  "什么是揉搓线洗盘？",
  "如何使用全市场扫描？",
];

export function RAGProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session_id] = useState(() => Math.random().toString(36).slice(2, 10));
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS);

  const query = useCallback(async (text: string, category?: QueryCategory) => {
    // 添加用户消息
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    try {
      const response: RAGQueryResponse = await queryKnowledge({
        query: text,
        category,
        session_id,
        top_k: 3,
      });

      // 添加助手消息
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        retrieved_docs: response.retrieved_docs,
        confidence: response.confidence,
        elapsed_ms: response.elapsed_ms,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // 更新建议
      if (response.suggestions.length > 0) {
        setSuggestions(response.suggestions);
      }
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? e?.message ?? "查询失败";
      setError(msg);
      // 添加错误消息
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `抱歉，查询出错：${msg}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }, [session_id]);

  const setOpen = useCallback((open: boolean) => {
    setIsOpen(open);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return (
    <RAGContext.Provider
      value={{
        messages,
        loading,
        error,
        session_id,
        isOpen,
        suggestions,
        query,
        setOpen,
        clearMessages,
      }}
    >
      {children}
    </RAGContext.Provider>
  );
}