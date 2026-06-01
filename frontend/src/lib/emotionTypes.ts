// ──────────────────────────────────────────────
// 打板情绪监控 — 类型定义（匹配后端 API v2）
// ──────────────────────────────────────────────

/** 涨停股条目 */
export interface LimitUpStock {
  code: string;
  name: string;
  firstLimitTime: string;
  lastLimitTime: string;
  sealAmount: number;
  floatCap: number;
  sealRatio: number;
  boardCount: number;
  tag: BoardTag;
  sector: string;
  reason: string;
  changePct: number;
  turnover: number;
  intraData: number[];
}

export type BoardTag =
  | "首板" | "二板一字" | "换手板" | "地天板"
  | "烂板回封" | "一字板" | "T字板" | "1板一字";

/** 连板梯队条目 */
export interface ConsecutiveBoard {
  code: string;
  name: string;
  boardCount: number;
  sealAmount: number;
  sealRatio: number;
  changePct: number;
  turnover: number;
  status: "封死" | "炸板" | "回落";
  tag: BoardTag;
  isHighest?: boolean;
  todayChangePct: number;
  todayOpenPct: number;
}

/** 连板今日表现追踪 */
export interface ConsecutiveTracking {
  code: string;
  name: string;
  boardCount: number;
  openPct: number;
  highPct: number;
  closePct: number;
  lowPct: number;
  status: string;
  statusColor: string;
  amount: number;
}

/** 炸板股条目 */
export interface BrokenBoard {
  code: string;
  name: string;
  highPct: number;
  currentPct: number;
  brokenDuration: number;
  brokenAmount: number;
  sector: string;
  boardCount: number;
  status: "观察" | "回封";
}

/** 炸板复盘排行 */
export interface BrokenReview {
  code: string;
  name: string;
  highPct: number;
  currentPct: number;
  pullback: number;
  amount: number;
  openPct: number;
}

/** 板块热力 */
export interface SectorHeat {
  sector: string;
  count: number;
  broken: number;
  totalAmount: number;
  stocks: Array<{ code: string; name: string; changePct: number; boardCount: number }>;
}

/** 龙头股对比 */
export interface LeaderStock {
  code: string;
  name: string;
  boardCount: number;
  changePct: number;
  sealAmount: number;
  turnover: number;
  tag: BoardTag;
  isHighest: boolean;
}

/** 晋级率 */
export interface PromotionRate {
  level: string;
  rate: number;
  success: number;
  total: number;
}

/** 顶部仪表盘数据 */
export interface SentimentMetrics {
  yesterdayLimitUpToday: number;
  brokenRate: number;
  limitUpCount: number;
  limitDownCount: number;
  promotionRate: PromotionRate;
  promotionRates: Record<string, PromotionRate>;
  compositeScore: number;
}

/** 后端返回的情绪快照 */
export interface EmotionSnapshot {
  date: string;
  fetchedAt: string;
  error?: string;
  metrics: SentimentMetrics;
  limitUpStocks: LimitUpStock[];
  consecutiveBoards: ConsecutiveBoard[];
  consecutiveTracking: ConsecutiveTracking[];
  brokenBoards: BrokenBoard[];
  sectorHeat: SectorHeat[];
  brokenReview: BrokenReview[];
  leaders: LeaderStock[];
}

export type RefreshRate = "12:00" | "14:30" | "manual";

export interface AlertConfig {
  soundEnabled: boolean;
  customSoundUrl: string | null;
  desktopNotify: boolean;
}

export interface EmotionState {
  snapshot: EmotionSnapshot | null;
  loading: boolean;
  error: string | null;
  lastFetch: string | null;
  nextFetch: string | null;
  refreshRate: RefreshRate;
  alerts: AlertConfig;
  benchmarkStock: LimitUpStock | null;
}
