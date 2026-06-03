"""
股票相关原子化 API 路由。

每条路由对应一个独立的数据维度/策略指标，便于未来升级为多 Agent 协作 Tool。
"""

import re
from typing import Optional, List

from fastapi import APIRouter, Query, HTTPException

from app.config import settings
from app.schemas.stock import HistoryResponse, KLineItem, SummaryResponse, StockSearchResult
from app.services.data_fetcher import fetch_history_daily, get_all_stock_codes
from app.services.strategy import generate_summary, run_strategy_pipeline

router = APIRouter(prefix="/stock", tags=["stock"])


def _validate_symbol(symbol: str) -> str:
    """
    验证并规范化股票代码。
    必须为6位数字，去除 sh/sz 前缀。
    """
    code = str(symbol).lower().strip()
    if code.startswith(("sh", "sz")):
        code = code[2:]
    if not re.match(r"^\d{6}$", code):
        raise HTTPException(
            status_code=400,
            detail=f"无效的股票代码 '{symbol}'，必须是6位数字（如 600519）"
        )
    return code


@router.get("/search", response_model=List[StockSearchResult])
def search_stocks(
    keyword: str = Query(default="", description="搜索关键词（代码或名称）"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
):
    """
    搜索股票（支持代码和名称搜索）。

    Returns:
        匹配的股票列表，包含代码和名称。
    """
    if not keyword:
        return []

    keyword = keyword.strip().upper()

    # 获取全部股票列表
    all_stocks = get_all_stock_codes()

    results = []
    for stock in all_stocks:
        code = stock.get("code", "")
        name = stock.get("name", "")

        # 匹配逻辑：代码前缀匹配或名称包含
        code_match = code.startswith(keyword)
        name_match = keyword.lower() in name.lower() if name else False

        if code_match or name_match:
            results.append(StockSearchResult(
                code=code,
                name=name,
                market=stock.get("market", 1),
            ))

            if len(results) >= limit:
                break

    return results


@router.get("/history", response_model=HistoryResponse)
def get_stock_history(
    symbol: str = Query(default=settings.DEFAULT_STOCK_CODE, description="股票代码"),
    limit: int = Query(default=120, ge=10, le=500, description="返回最近 N 条"),
):
    """
    获取带策略指标的历史日 K 线序列。
    包含：OHLCV + 6条均线 + MACD(DIF/DEA/HIST)。
    """
    code = _validate_symbol(symbol)
    df = fetch_history_daily(code)
    df.attrs["symbol"] = code
    df = run_strategy_pipeline(df)

    # 取最近 N 条
    df = df.tail(limit).reset_index(drop=True)

    records = []
    for _, row in df.iterrows():
        item = KLineItem(
            date=str(row["date"].date()),
            open=round(row["open"], 2),
            high=round(row["high"], 2),
            low=round(row["low"], 2),
            close=round(row["close"], 2),
            volume=round(row["volume"], 0),
            ma5=round(row["ma5"], 2) if "ma5" in row and row["ma5"] == row["ma5"] else None,
            ma10=round(row["ma10"], 2) if "ma10" in row and row["ma10"] == row["ma10"] else None,
            ma20=round(row["ma20"], 2) if "ma20" in row and row["ma20"] == row["ma20"] else None,
            ma30=round(row["ma30"], 2) if "ma30" in row and row["ma30"] == row["ma30"] else None,
            ma55=round(row["ma55"], 2) if "ma55" in row and row["ma55"] == row["ma55"] else None,
            ma60=round(row["ma60"], 2) if "ma60" in row and row["ma60"] == row["ma60"] else None,
            boll_upper=round(row["boll_upper"], 2) if "boll_upper" in row and row["boll_upper"] == row["boll_upper"] else None,
            boll_mid=round(row["boll_mid"], 2) if "boll_mid" in row and row["boll_mid"] == row["boll_mid"] else None,
            boll_lower=round(row["boll_lower"], 2) if "boll_lower" in row and row["boll_lower"] == row["boll_lower"] else None,
            dif=round(row["dif"], 4) if "dif" in row and row["dif"] == row["dif"] else None,
            dea=round(row["dea"], 4) if "dea" in row and row["dea"] == row["dea"] else None,
            macd_hist=round(row["macd_hist"], 4) if "macd_hist" in row and row["macd_hist"] == row["macd_hist"] else None,
        )
        records.append(item)

    return HistoryResponse(symbol=symbol, total=len(records), data=records)


@router.get("/summary", response_model=SummaryResponse)
def get_stock_summary(
    symbol: str = Query(default=settings.DEFAULT_STOCK_CODE, description="股票代码"),
):
    """
    获取最新策略复盘摘要。
    包含：均线状态、MACD 多周期状态、成交量信号、综合打分。
    """
    code = _validate_symbol(symbol)
    df = fetch_history_daily(code)
    df.attrs["symbol"] = code
    summary = generate_summary(df)
    summary["symbol"] = code
    return SummaryResponse(**summary)
