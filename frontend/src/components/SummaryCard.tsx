"use client";

import type { SummaryResponse } from "@/lib/api";

interface Props {
  summary: SummaryResponse | null;
  loading: boolean;
}

const scoreColor = (score: number) => {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-yellow-400";
  if (score >= 40) return "text-orange-400";
  return "text-red-400";
};

const scoreBg = (score: number) => {
  if (score >= 80) return "bg-emerald-400/10 border-emerald-400/30";
  if (score >= 60) return "bg-yellow-400/10 border-yellow-400/30";
  if (score >= 40) return "bg-orange-400/10 border-orange-400/30";
  return "bg-red-400/10 border-red-400/30";
};

const StatusBadge = ({ ok, label }: { ok: boolean; label: string }) => (
  <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
    <div className="text-xs text-slate-500 mb-1">{label}</div>
    <div className={`text-sm font-semibold ${ok ? "text-emerald-400" : "text-slate-400"}`}>
      {ok ? "是 ✓" : "否 ✗"}
    </div>
  </div>
);

export default function SummaryCard({ summary, loading }: Props) {
  if (loading) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-6 animate-pulse">
        <div className="h-4 bg-slate-700 rounded w-32 mb-4" />
        <div className="h-8 bg-slate-700 rounded w-20 mb-4" />
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-3 bg-slate-700 rounded w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-6 text-slate-400 text-center">
        暂无数据
      </div>
    );
  }

  const rub = summary.rubbing_strategy;

  return (
    <div className="space-y-6">
      {/* ====== 主面板 ====== */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-6">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-100">策略复盘摘要</h2>
            <p className="text-xs text-slate-500 mt-1">
              {summary.symbol} · {summary.latest_date} · 收盘 {summary.latest_close}
            </p>
          </div>
          {/* 综合打分 */}
          <div
            className={`flex items-center justify-center w-16 h-16 rounded-xl border-2 ${scoreBg(summary.strategy_score)}`}
          >
            <div className="text-center">
              <div className={`text-2xl font-black ${scoreColor(summary.strategy_score)}`}>
                {summary.strategy_score}
              </div>
              <div className="text-[10px] text-slate-400 -mt-1">分</div>
            </div>
          </div>
        </div>

        {/* 信号列表 */}
        <div className="space-y-2">
          {summary.signal_summary.map((sig, i) => (
            <div
              key={i}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-sm text-slate-300"
            >
              <span>{sig}</span>
            </div>
          ))}
        </div>

        {/* MACD 详情 */}
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            MACD 多周期状态
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {(["monthly", "weekly", "daily"] as const).map((period) => {
              const m = summary.macd[period] as {
                dif: number | null;
                dea: number | null;
                golden_cross?: boolean | null;
                death_cross?: boolean | null;
                hist?: number | null;
              };
              const label = period === "monthly" ? "月线" : period === "weekly" ? "周线" : "日线";
              const isGolden = m.golden_cross === true;
              const isDeath = m.death_cross === true;
              const statusColor = isGolden ? "text-emerald-400" : isDeath ? "text-red-400" : "text-slate-400";
              const statusText = isGolden ? "金叉" : isDeath ? "死叉" : "中性";

              return (
                <div key={period} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                  <div className="text-xs text-slate-500 mb-1">{label}</div>
                  <div className="text-sm font-mono text-slate-200">DIF: {m.dif ?? "—"}</div>
                  <div className="text-sm font-mono text-slate-200">DEA: {m.dea ?? "—"}</div>
                  {m.hist !== undefined && m.hist !== null && (
                    <div className="text-sm font-mono text-slate-200">HIST: {m.hist}</div>
                  )}
                  <div className={`text-xs font-semibold mt-1 ${statusColor}`}>{statusText}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 成交量信号 */}
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            成交量异动检测
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <StatusBadge ok={summary.volume_signal.volume_decreasing_3d} label="近 3 日量递减" />
            <StatusBadge ok={summary.volume_signal.volume_below_monthly_avg} label="低于月均量" />
            {summary.volume_signal.monthly_avg_volume && (
              <div className="col-span-2 bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                <div className="text-xs text-slate-500 mb-1">近 20 日均量</div>
                <div className="text-sm font-mono text-slate-200">
                  {summary.volume_signal.monthly_avg_volume.toLocaleString()}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ====== 红色揉搓线策略面板 ====== */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-100">
            <span className="text-orange-400 mr-1">🔥</span>红色揉搓线策略
          </h2>
          {rub.buy_signal ? (
            <span className="px-3 py-1 text-xs font-bold rounded-full bg-emerald-400/20 text-emerald-400 border border-emerald-400/30 animate-pulse">
              BUY 信号！
            </span>
          ) : (
            <span className="px-3 py-1 text-xs font-bold rounded-full bg-slate-700 text-slate-400">
              未触发
            </span>
          )}
        </div>

        {/* 四条件网格 */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          <StatusBadge ok={rub.is_near_boll_mid} label="① BOLL 中轨附近" />
          <StatusBadge ok={rub.had_new_high} label="② 近 5 日创 20 日新高" />
          <StatusBadge ok={rub.is_shrink_vol} label="③ 缩量 (≤ 60%)" />
          <StatusBadge ok={rub.rubbing_line.is_rubbing_line} label="④ 红色揉搓线形态" />
        </div>

        {/* BOLL 数据 */}
        <div className="pt-4 border-t border-slate-700/50">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            BOLL 参数 (20, 2)
          </h3>
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">上轨</div>
              <div className="text-sm font-mono text-purple-400">{summary.boll.upper ?? "—"}</div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">中轨</div>
              <div className="text-sm font-mono text-yellow-400">{summary.boll.mid ?? "—"}</div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">下轨</div>
              <div className="text-sm font-mono text-purple-400">{summary.boll.lower ?? "—"}</div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">偏离中轨</div>
              <div className={`text-sm font-mono ${
                (summary.boll.close_near_mid_pct ?? 999) <= 1 ? "text-emerald-400" : "text-slate-200"
              }`}>
                {summary.boll.close_near_mid_pct != null ? `${summary.boll.close_near_mid_pct}%` : "—"}
              </div>
            </div>
          </div>
        </div>

        {/* K 线形态细节 */}
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            K 线形态拆解
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">K-2（前一根）阳线 + 长上影</div>
              <div className="flex gap-4 text-sm font-mono text-slate-200">
                <span>阳线: {rub.rubbing_line.k1_is_red ? "✓" : "✗"}</span>
                <span>长上影: {rub.rubbing_line.k1_is_long_upper ? "✓" : "✗"}</span>
                <span>上影/体比: {rub.rubbing_line.k1_upper_ratio != null ? `${rub.rubbing_line.k1_upper_ratio}x` : "—"}</span>
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">K-1（最新）阳线 + 长下影</div>
              <div className="flex gap-4 text-sm font-mono text-slate-200">
                <span>阳线: {rub.rubbing_line.k2_is_red ? "✓" : "✗"}</span>
                <span>长下影: {rub.rubbing_line.k2_is_long_lower ? "✓" : "✗"}</span>
                <span>下影/体比: {rub.rubbing_line.k2_lower_ratio != null ? `${rub.rubbing_line.k2_lower_ratio}x` : "—"}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
