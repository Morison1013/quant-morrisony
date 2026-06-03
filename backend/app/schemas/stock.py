from pydantic import BaseModel
from typing import Optional


class StockSearchResult(BaseModel):
    """股票搜索结果。"""
    code: str
    name: str
    market: int = 1  # 0=深圳, 1=上海


class KLineItem(BaseModel):
    """单根 K 线数据（带策略指标）。"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma30: Optional[float] = None
    ma55: Optional[float] = None
    ma60: Optional[float] = None
    boll_upper: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_lower: Optional[float] = None
    dif: Optional[float] = None
    dea: Optional[float] = None
    macd_hist: Optional[float] = None


class HistoryResponse(BaseModel):
    """GET /api/stock/history 响应。"""
    symbol: str
    total: int
    data: list[KLineItem]


class VolumeSignal(BaseModel):
    is_arbitrage_signal: bool
    volume_decreasing_3d: bool
    volume_below_monthly_avg: bool
    monthly_avg_volume: Optional[float] = None


class BollStatus(BaseModel):
    upper: Optional[float] = None
    mid: Optional[float] = None
    lower: Optional[float] = None
    close_near_mid_pct: Optional[float] = None


class RubbingLineDetail(BaseModel):
    is_rubbing_line: bool
    k1_is_red: bool
    k2_is_red: bool
    k1_is_long_upper: bool
    k2_is_long_lower: bool
    k1_upper_ratio: Optional[float] = None
    k2_lower_ratio: Optional[float] = None


class RubbingStrategy(BaseModel):
    buy_signal: bool
    is_near_boll_mid: bool
    had_new_high: bool
    is_shrink_vol: bool
    rubbing_line: RubbingLineDetail


class SummaryResponse(BaseModel):
    """GET /api/stock/summary 响应。"""
    symbol: str
    latest_date: str
    latest_close: float
    strategy_score: int
    ma_bullish_alignment: bool
    macd: dict
    volume_signal: VolumeSignal
    boll: BollStatus
    rubbing_strategy: RubbingStrategy
    signal_summary: list[str]


# ────────────────────────────────────────────
# 全市场扫描 Schema
# ────────────────────────────────────────────

class ScanResultItem(BaseModel):
    """单只匹配股票的结果。"""
    code: str
    name: str
    close: float
    latest_date: str
    strategy_score: int
    matched_strategies: list[str]


class ScanResponse(BaseModel):
    """GET /api/scanner/scan 响应。"""
    total: int
    matched: int
    skipped: int
    elapsed_ms: int
    results: list[ScanResultItem]
    error: Optional[str] = None

