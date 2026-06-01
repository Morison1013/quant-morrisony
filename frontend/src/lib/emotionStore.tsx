"use client";

// ──────────────────────────────────────────────
// 打板情绪监控 — 全局状态管理（API 版）
// ──────────────────────────────────────────────

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import type {
  EmotionState,
  AlertConfig,
  LimitUpStock,
} from "./emotionTypes";
import { fetchEmotionSnapshot } from "./emotionApi";

interface EmotionContextType extends EmotionState {
  refresh: () => Promise<void>;
  setAlerts: (alerts: AlertConfig) => void;
  setBenchmarkStock: (stock: LimitUpStock | null) => void;
}

const EmotionContext = createContext<EmotionContextType | null>(null);

export function useEmotion() {
  const ctx = useContext(EmotionContext);
  if (!ctx) throw new Error("useEmotion must be used within EmotionProvider");
  return ctx;
}

function initState(): EmotionState {
  return {
    snapshot: null,
    loading: true,
    error: null,
    lastFetch: null,
    nextFetch: null,
    refreshRate: "12:00",
    alerts: { soundEnabled: true, customSoundUrl: null, desktopNotify: true },
    benchmarkStock: null,
  };
}

/**
 * 计算距离下一个复盘时间点的毫秒数。
 * 复盘时间点：12:00（午间）和 14:30（尾盘）。
 */
function getNextReviewTime(): { ms: number; label: string } {
  const now = new Date();
  const h = now.getHours();
  const m = now.getMinutes();
  const currentMin = h * 60 + m;

  const noonTarget = 12 * 60;
  const eveningTarget = 14 * 60 + 30;

  let target: number;
  let label: string;

  if (currentMin < noonTarget) {
    target = noonTarget;
    label = "12:00 午间复盘";
  } else if (currentMin < eveningTarget) {
    target = eveningTarget;
    label = "14:30 尾盘复盘";
  } else {
    target = noonTarget + 24 * 60;
    label = "次日 12:00 午间复盘";
  }

  const diffMin = target - currentMin;
  const ms = diffMin * 60 * 1000;
  return { ms: Math.max(ms, 60000), label };
}

function formatNextFetch(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  if (h > 0) return `${h}小时${m}分`;
  return `${m}分钟`;
}

export function EmotionProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<EmotionState>(initState);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doRefresh = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      const snapshot = await fetchEmotionSnapshot();
      const next = getNextReviewTime();
      setState((prev) => ({
        ...prev,
        snapshot,
        loading: false,
        error: snapshot.error || null,
        lastFetch: new Date().toLocaleTimeString("zh-CN"),
        nextFetch: formatNextFetch(next.ms),
      }));
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? e?.message ?? "数据加载失败";
      setState((prev) => ({
        ...prev,
        snapshot: null,
        loading: false,
        error: msg,
        lastFetch: new Date().toLocaleTimeString("zh-CN"),
      }));
    }
  }, []);

  const refresh = useCallback(async () => {
    await doRefresh();
  }, [doRefresh]);

  // 初始加载
  useEffect(() => {
    doRefresh();
  }, [doRefresh]);

  // 设置复盘定时器：12:00 和 14:30 自动拉取
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    const next = getNextReviewTime();
    timerRef.current = setTimeout(() => {
      doRefresh();
    }, next.ms);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [doRefresh]);

  const setAlerts = useCallback((alerts: AlertConfig) => {
    setState((prev) => ({ ...prev, alerts }));
  }, []);

  const setBenchmarkStock = useCallback((stock: LimitUpStock | null) => {
    setState((prev) => ({ ...prev, benchmarkStock: stock }));
  }, []);

  return (
    <EmotionContext.Provider
      value={{
        snapshot: state.snapshot,
        loading: state.loading,
        error: state.error,
        lastFetch: state.lastFetch,
        nextFetch: state.nextFetch,
        refreshRate: state.refreshRate,
        alerts: state.alerts,
        benchmarkStock: state.benchmarkStock,
        refresh,
        setAlerts,
        setBenchmarkStock,
      }}
    >
      {children}
    </EmotionContext.Provider>
  );
}
