"""
全市场扫描 API 路由。

提供股票扫描接口，用户可勾选策略进行全市场筛选。
"""

from fastapi import APIRouter, Query

from app.schemas.stock import ScanResponse, ScanResultItem
from app.services.scanner import STRATEGY_FLAGS, scan_stocks

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/scan", response_model=ScanResponse)
def scan_market(
    ma_bullish: bool = Query(default=False, description="均线多头排列（60/55/30/20/10/5 全向上）"),
    macd_golden: bool = Query(default=False, description="月MACD金叉且周/日未死叉"),
    arbitrage: bool = Query(default=False, description="隔日套利信号（量缩价稳）"),
    rubbing: bool = Query(default=False, description="红色揉搓线 BUY 信号"),
):
    """
    全市场扫描：返回满足所有选中策略的股票列表。

    结果按 strategy_score 降序排列。
    """
    strategies = []
    if ma_bullish:
        strategies.append("ma_bullish")
    if macd_golden:
        strategies.append("macd_golden")
    if arbitrage:
        strategies.append("arbitrage")
    if rubbing:
        strategies.append("rubbing")

    result = scan_stocks(strategies)

    return ScanResponse(
        total=result["total"],
        matched=result["matched"],
        skipped=result["skipped"],
        elapsed_ms=result["elapsed_ms"],
        results=[ScanResultItem(**r) for r in result.get("results", [])],
        error=result.get("error"),
    )


@router.get("/strategies")
def list_strategies():
    """
    获取所有可用的策略标志及描述。
    """
    return {"strategies": STRATEGY_FLAGS}


@router.get("/db-stats")
def db_stats():
    """
    获取本地数据库统计信息。
    """
    from app.services.db import get_db_stats, get_last_refresh

    stats = get_db_stats()
    stats["last_refresh"] = get_last_refresh()
    return stats
