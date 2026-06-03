"use client";

import React, { useState, useEffect, useRef } from "react";
import Header from "@/components/Header";
import KLineChart from "@/components/KLineChart";
import SummaryCard from "@/components/SummaryCard";
import { fetchHistory, fetchSummary, searchStocks, type KLineItem, type SummaryResponse, type StockSearchItem } from "@/lib/api";

export default function StockQueryPage() {
  const [symbol, setSymbol] = useState("600519");
  const [stockName, setStockName] = useState("贵州茅台");
  const [history, setHistory] = useState<KLineItem[]>([]);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 搜索相关状态
  const [searchKeyword, setSearchKeyword] = useState("");
  const [searchResults, setSearchResults] = useState<StockSearchItem[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  const loadData = async (code: string) => {
    setLoading(true);
    setError(null);
    try {
      const [h, s] = await Promise.all([fetchHistory(code), fetchSummary(code)]);
      setHistory(h.data);
      setSummary(s);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "数据加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(symbol);
  }, [symbol]);

  // 搜索股票
  useEffect(() => {
    const doSearch = async () => {
      if (!searchKeyword.trim()) {
        setSearchResults([]);
        setShowDropdown(false);
        return;
      }

      setSearching(true);
      try {
        const results = await searchStocks(searchKeyword, 10);
        setSearchResults(results);
        setShowDropdown(results.length > 0);
      } catch (e) {
        setSearchResults([]);
        setShowDropdown(false);
      } finally {
        setSearching(false);
      }
    };

    // 延迟搜索（防抖）
    const timer = setTimeout(doSearch, 200);
    return () => clearTimeout(timer);
  }, [searchKeyword]);

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectStock = (stock: StockSearchItem) => {
    setSymbol(stock.code);
    setStockName(stock.name);
    setSearchKeyword("");
    setShowDropdown(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchKeyword.trim()) {
      // 如果有搜索结果，选择第一个
      if (searchResults.length > 0) {
        handleSelectStock(searchResults[0]);
      } else {
        // 否则直接用输入的内容作为代码
        setSymbol(searchKeyword.trim());
        setStockName("");
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 股票搜索输入 */}
        <div className="bg-slate-900 rounded-xl border border-slate-700 p-4">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-300">股票搜索：</label>

            {/* 搜索框容器 */}
            <div ref={searchRef} className="relative flex-1 max-w-md">
              <input
                type="text"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
                placeholder="输入代码或名称（如：600519 或 茅台）"
                className="w-full px-3 py-2 text-sm rounded-lg bg-slate-800 border border-slate-600 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />

              {/* 搜索下拉框 */}
              {showDropdown && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-600 rounded-lg shadow-lg overflow-hidden z-50">
                  {searching ? (
                    <div className="px-4 py-2 text-sm text-slate-400 text-center">
                      搜索中...
                    </div>
                  ) : searchResults.length > 0 ? (
                    <ul className="max-h-64 overflow-y-auto">
                      {searchResults.map((stock) => (
                        <li
                          key={stock.code}
                          onClick={() => handleSelectStock(stock)}
                          className="px-4 py-2 hover:bg-slate-700 cursor-pointer flex items-center gap-3"
                        >
                          <span className="font-mono text-blue-400">{stock.code}</span>
                          <span className="text-slate-200">{stock.name}</span>
                          <span className="text-xs text-slate-500">
                            {stock.market === 1 ? "沪" : "深"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="px-4 py-2 text-sm text-slate-400 text-center">
                      未找到匹配的股票
                    </div>
                  )}
                </div>
              )}
            </div>

            <button
              type="submit"
              className="px-6 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 transition-colors font-medium"
            >
              查询
            </button>
          </form>

          {/* 当前选择的股票 */}
          {symbol && (
            <div className="mt-3 flex items-center gap-2 text-sm">
              <span className="text-slate-500">当前股票：</span>
              <span className="font-mono text-blue-400">{symbol}</span>
              {stockName && (
                <span className="text-slate-300">· {stockName}</span>
              )}
              {summary && (
                <span className="text-xs text-slate-500">
                  ({summary.latest_date} 收盘 {summary.latest_close})
                </span>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl px-4 py-3 text-red-300 text-sm">
            ⚠️ {error} — 请确认后端服务已启动（localhost:8000）
          </div>
        )}

        {/* K 线图 */}
        <KLineChart data={history} loading={loading} />

        {/* 策略复盘摘要 */}
        <SummaryCard summary={summary} loading={loading} />
      </main>

      <footer className="border-t border-slate-800 mt-12 py-4 text-center text-xs text-slate-600">
        Quant_Morrisony · A 股量化看盘助手 · 数据源 通达信(pytdx) · 仅供个人复盘参考，不构成投资建议
      </footer>
    </div>
  );
}