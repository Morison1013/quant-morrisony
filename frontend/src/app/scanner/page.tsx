"use client";

import React, { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import { fetchScan, fetchDbStats, type ScanResultItem } from "@/lib/api";

const STRATEGIES = [
  { key: "ma_bullish", label: "均线多头排列", desc: "60/55/30/20/10/5 全向上" },
  { key: "macd_golden", label: "月MACD金叉", desc: "月金叉 + 周/日未死叉" },
  { key: "arbitrage", label: "隔日套利信号", desc: "量缩价稳，3日递减" },
  { key: "rubbing", label: "揉搓线洗盘", desc: "近3日多空拉锯 + 缩量" },
];

const scoreColor = (score: number) => {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-yellow-400";
  if (score >= 40) return "text-orange-400";
  return "text-red-400";
};

export default function ScannerPage() {
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [results, setResults] = useState<ScanResultItem[]>([]);
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dbStats, setDbStats] = useState<{ stock_count: number; kline_count: number; last_refresh: string | null } | null>(null);

  // Load DB stats
  useEffect(() => {
    fetchDbStats().then(setDbStats).catch(() => {});
  }, []);

  const toggle = (key: string) => {
    setSelected((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleScan = useCallback(async () => {
    const active = Object.entries(selected)
      .filter(([, v]) => v)
      .map(([k]) => k);

    if (active.length === 0) {
      setError("请至少选择一个策略");
      return;
    }

    setScanning(true);
    setError(null);
    setResults([]);
    setProgress(null);
    setElapsed(null);

    const startTime = Date.now();

    try {
      // Polling: since the API is synchronous, we show a loading state
      // In a real app, you'd use SSE or WebSockets for progress updates
      setProgress({ current: 0, total: 1 }); // show "starting..."

      const scanResults = await fetchScan(active);
      setResults(scanResults.results);
      setElapsed(scanResults.elapsed_ms);
      setProgress({ current: scanResults.total, total: scanResults.total });
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "扫描失败");
    } finally {
      setScanning(false);
    }
  }, [selected]);

  const activeCount = Object.values(selected).filter(Boolean).length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 数据库状态 */}
        {dbStats && (
          <div className="bg-slate-900 rounded-xl border border-slate-700 p-4 flex items-center justify-between">
            <div className="flex items-center gap-6 text-sm">
              <div>
                <span className="text-slate-500">本地数据库</span>
                <span className="ml-2 text-emerald-400 font-medium">● 已缓存</span>
              </div>
              <div className="text-slate-400">
                <span className="text-slate-500">股票: </span>
                <span className="font-mono">{dbStats.stock_count.toLocaleString()}</span>
              </div>
              <div className="text-slate-400">
                <span className="text-slate-500">K线: </span>
                <span className="font-mono">{dbStats.kline_count.toLocaleString()}</span>
              </div>
            </div>
            <div className="text-xs text-slate-500">
              {dbStats.last_refresh ? `最后更新: ${dbStats.last_refresh}` : "未刷新"}
            </div>
          </div>
        )}

        {/* 策略选择面板 */}
        <div className="bg-slate-900 rounded-xl border border-slate-700 p-6">
          <h2 className="text-lg font-bold text-slate-100 mb-4">全市场扫描</h2>
          <p className="text-xs text-slate-500 mb-4">
            勾选策略，系统自动扫描全部 A 股（本地数据库加速）。
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {STRATEGIES.map((s) => (
              <label
                key={s.key}
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  selected[s.key]
                    ? "bg-blue-600/10 border-blue-500/50"
                    : "bg-slate-800/50 border-slate-700/50 hover:border-slate-600"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selected[s.key] || false}
                  onChange={() => toggle(s.key)}
                  className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
                />
                <div>
                  <div className="text-sm font-medium text-slate-200">{s.label}</div>
                  <div className="text-xs text-slate-500">{s.desc}</div>
                </div>
              </label>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">
              已选 {activeCount} 个策略 · 预计扫描 ~5500 只沪深主板股票
            </span>
            <button
              onClick={handleScan}
              disabled={scanning || activeCount === 0}
              className={`px-6 py-2 text-sm rounded-lg font-medium transition-colors ${
                scanning || activeCount === 0
                  ? "bg-slate-700 text-slate-500 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-500 text-white"
              }`}
            >
              {scanning ? "扫描中..." : "开始扫描"}
            </button>
          </div>

          {/* 进度条 */}
          {scanning && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span>正在扫描全市场...</span>
                <span>
                  {progress ? `${progress.current.toLocaleString()} / ${progress.total.toLocaleString()}` : "准备中..."}
                </span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 rounded-full transition-all duration-300 animate-pulse"
                  style={{ width: progress ? `${(progress.current / progress.total) * 100}%` : "5%" }}
                />
              </div>
            </div>
          )}

          {elapsed !== null && !scanning && (
            <div className="mt-3 text-xs text-slate-500">
              扫描完成 · 耗时 {(elapsed / 1000).toFixed(1)}s
            </div>
          )}

          {error && (
            <div className="mt-3 bg-red-900/30 border border-red-700/50 rounded-lg px-4 py-2 text-red-300 text-sm">
              ⚠️ {error}
            </div>
          )}
        </div>

        {/* 结果表格 */}
        {results.length > 0 && (
          <div className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden">
            <div className="px-6 py-3 border-b border-slate-700/50 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200">
                匹配结果
                <span className="ml-2 text-xs text-emerald-400">
                  {results.length} 只
                </span>
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50 text-slate-400 text-xs uppercase tracking-wider">
                    <th className="px-6 py-2 text-left font-medium">排名</th>
                    <th className="px-6 py-2 text-left font-medium">代码</th>
                    <th className="px-6 py-2 text-left font-medium">名称</th>
                    <th className="px-6 py-2 text-right font-medium">最新价</th>
                    <th className="px-6 py-2 text-center font-medium">打分</th>
                    <th className="px-6 py-2 text-left font-medium">匹配策略</th>
                    <th className="px-6 py-2 text-center font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr
                      key={r.code}
                      className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="px-6 py-3 text-slate-500 font-mono">{i + 1}</td>
                      <td className="px-6 py-3 font-mono text-slate-200">{r.code}</td>
                      <td className="px-6 py-3 text-slate-200">{r.name || "—"}</td>
                      <td className="px-6 py-3 text-right font-mono text-slate-200">{r.close}</td>
                      <td className={`px-6 py-3 text-center font-bold ${scoreColor(r.strategy_score)}`}>
                        {r.strategy_score}
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex flex-wrap gap-1">
                          {r.matched_strategies.map((s) => {
                            const label = STRATEGIES.find((st) => st.key === s)?.label || s;
                            return (
                              <span
                                key={s}
                                className="px-2 py-0.5 text-xs rounded-full bg-blue-600/20 text-blue-400 border border-blue-600/30"
                              >
                                {label}
                              </span>
                            );
                          })}
                        </div>
                      </td>
                      <td className="px-6 py-3 text-center">
                        <Link
                          href={`/stock/${r.code}`}
                          className="text-blue-400 hover:text-blue-300 text-xs font-medium"
                        >
                          详情 →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 无结果 */}
        {!scanning && results.length === 0 && elapsed !== null && (
          <div className="bg-slate-900 rounded-xl border border-slate-700 p-12 text-center">
            <div className="text-4xl mb-3">🔍</div>
            <div className="text-slate-300 font-medium">未找到匹配的股票</div>
            <div className="text-xs text-slate-500 mt-1">
              尝试减少勾选的策略，或调整筛选条件
            </div>
          </div>
        )}

        {/* 初始状态 */}
        {!scanning && results.length === 0 && elapsed === null && (
          <div className="bg-slate-900 rounded-xl border border-slate-700 p-12 text-center">
            <div className="text-4xl mb-3">📊</div>
            <div className="text-slate-300 font-medium">选择策略后点击「开始扫描」</div>
            <div className="text-xs text-slate-500 mt-1">
              系统将遍历全部 A 股，筛选同时满足条件的股票
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-800 mt-12 py-4 text-center text-xs text-slate-600">
        Quant_Morrisony · A 股量化看盘助手 · 数据源 通达信(pytdx) · 仅供个人复盘参考，不构成投资建议
      </footer>
    </div>
  );
}
