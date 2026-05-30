import axios from "axios";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

export interface KLineItem {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma5?: number | null;
  ma10?: number | null;
  ma20?: number | null;
  ma30?: number | null;
  ma55?: number | null;
  ma60?: number | null;
  boll_upper?: number | null;
  boll_mid?: number | null;
  boll_lower?: number | null;
  dif?: number | null;
  dea?: number | null;
  macd_hist?: number | null;
}

export interface HistoryResponse {
  symbol: string;
  total: number;
  data: KLineItem[];
}

export interface VolumeSignal {
  is_arbitrage_signal: boolean;
  volume_decreasing_3d: boolean;
  volume_below_monthly_avg: boolean;
  monthly_avg_volume: number | null;
}

export interface SummaryResponse {
  symbol: string;
  latest_date: string;
  latest_close: number;
  strategy_score: number;
  ma_bullish_alignment: boolean;
  macd: {
    monthly: { dif: number | null; dea: number | null; golden_cross: boolean | null };
    weekly: { dif: number | null; dea: number | null; death_cross: boolean | null };
    daily: { dif: number | null; dea: number | null; hist: number | null; death_cross: boolean | null };
  };
  volume_signal: VolumeSignal;
  boll: {
    upper: number | null;
    mid: number | null;
    lower: number | null;
    close_near_mid_pct: number | null;
  };
  rubbing_strategy: {
    buy_signal: boolean;
    is_near_boll_mid: boolean;
    had_new_high: boolean;
    is_shrink_vol: boolean;
    rubbing_line: {
      is_rubbing_line: boolean;
      k1_is_red: boolean;
      k2_is_red: boolean;
      k1_is_long_upper: boolean;
      k2_is_long_lower: boolean;
      k1_upper_ratio: number | null;
      k2_lower_ratio: number | null;
    };
  };
  signal_summary: string[];
}

export async function fetchHistory(symbol: string = "600519"): Promise<HistoryResponse> {
  const { data } = await api.get<HistoryResponse>("/stock/history", {
    params: { symbol, limit: 120 },
  });
  return data;
}

export async function fetchSummary(symbol: string = "600519"): Promise<SummaryResponse> {
  const { data } = await api.get<SummaryResponse>("/stock/summary", {
    params: { symbol },
  });
  return data;
}

// ────────────────────────────────────────────
// Scanner API
// ────────────────────────────────────────────

export interface ScanResultItem {
  code: string;
  name: string;
  close: number;
  latest_date: string;
  strategy_score: number;
  matched_strategies: string[];
}

export interface ScanResponse {
  total: number;
  matched: number;
  skipped: number;
  elapsed_ms: number;
  results: ScanResultItem[];
  error?: string | null;
}

export async function fetchScan(strategies: string[]): Promise<ScanResponse> {
  const params: Record<string, boolean> = {};
  strategies.forEach((s) => {
    params[s] = true;
  });

  // Increase timeout for scan (can take several minutes)
  const { data } = await api.get<ScanResponse>("/scanner/scan", {
    params,
    timeout: 600000, // 10 minutes
  });
  return data;
}

export async function fetchDbStats(): Promise<{
  stock_count: number;
  kline_count: number;
  date_from: string | null;
  date_to: string | null;
  last_refresh: string | null;
}> {
  const { data } = await api.get("/scanner/db-stats");
  return data;
}

// ────────────────────────────────────────────
// Dashboard API
// ────────────────────────────────────────────

export interface DashboardKLineItem {
  date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  amount?: number | null;
  ma5?: number | null;
  ma10?: number | null;
  ma20?: number | null;
  ma30?: number | null;
  ma55?: number | null;
  ma60?: number | null;
}

export interface IndexListItem {
  code: string;
  name: string;
  market: number;
}

export interface IndexHistoryResponse {
  symbol: string;
  name: string;
  frequency: string;
  total: number;
  data: DashboardKLineItem[];
}

export interface SectorListItem {
  code: string;
  name: string;
}

export interface SectorCategory {
  category: string;
  sectors: SectorListItem[];
}

export interface SectorCategoryResponse {
  categories: SectorCategory[];
}

export interface SectorHistoryResponse {
  symbol: string;
  name: string;
  frequency: string;
  total: number;
  data: DashboardKLineItem[];
}

export async function fetchIndices(): Promise<IndexListItem[]> {
  const { data } = await api.get<{ indices: IndexListItem[] }>("/dashboard/indices");
  return data.indices;
}

export async function fetchIndexHistory(
  symbol: string,
  frequency: string = "daily",
  limit: number = 120
): Promise<IndexHistoryResponse> {
  const { data } = await api.get<IndexHistoryResponse>(
    `/dashboard/index/${symbol}/history`,
    { params: { frequency, limit } }
  );
  return data;
}

export async function fetchSectors(): Promise<SectorListItem[]> {
  const { data } = await api.get<{ sectors: SectorListItem[] }>("/dashboard/sectors");
  return data.sectors;
}

export async function fetchSectorCategories(): Promise<SectorCategoryResponse> {
  const { data } = await api.get<SectorCategoryResponse>("/dashboard/sector-categories");
  return data;
}

export async function fetchSectorHistory(
  symbol: string,
  frequency: string = "daily",
  limit: number = 120
): Promise<SectorHistoryResponse> {
  const { data } = await api.get<SectorHistoryResponse>(
    `/dashboard/sector/${symbol}/history`,
    { params: { frequency, limit } }
  );
  return data;
}
