"""
指数 & 板块 API 路由。

原子化接口，便于后续升级为独立 Tool。
"""

from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.dashboard import (
    IndexHistoryResponse,
    IndexKLineItem,
    IndexListResponse,
    IndexListItem,
    SectorHistoryResponse,
    SectorListResponse,
    SectorListItem,
    SectorCategoryResponse,
    SectorCategory,
)
from app.services.data_fetcher_index import (
    INDICES,
    FREQ_5MIN,
    FREQ_DAILY,
    FREQ_WEEKLY,
    FREQ_MONTHLY,
    fetch_index_kline,
    list_indices,
)
from app.services.data_fetcher_sector import (
    SECTORS,
    FREQ_5MIN as SECTOR_5MIN,
    FREQ_DAILY as SECTOR_DAILY,
    FREQ_WEEKLY as SECTOR_WEEKLY,
    FREQ_MONTHLY as SECTOR_MONTHLY,
    fetch_sector_kline,
    list_sectors,
    list_sector_categories,
)
from app.services.strategy import compute_ma

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _build_kline_items(df, limit: int) -> list:
    """通用 K 线数据转换。"""
    df = compute_ma(df)  # 添加均线
    df = df.tail(limit).reset_index(drop=True)

    items = []
    for _, row in df.iterrows():
        item = {
            "date": str(row["date"].date()),
            "open": round(float(row["open"]), 2),
            "close": round(float(row["close"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "volume": round(float(row["volume"]), 0),
        }
        for p in [5, 10, 20, 30, 55, 60]:
            val = row.get(f"ma{p}")
            item[f"ma{p}"] = round(float(val), 2) if val == val else None
        if "amount" in row:
            item["amount"] = round(float(row["amount"]), 0)
        items.append(item)
    return items


# ────────────────────────────────────────────
# 指数接口
# ────────────────────────────────────────────

@router.get("/indices", response_model=IndexListResponse)
def get_index_list():
    """获取所有可用指数列表。"""
    indices = list_indices()
    return IndexListResponse(indices=[IndexListItem(**idx) for idx in indices])


@router.get("/index/{symbol}/history", response_model=IndexHistoryResponse)
def get_index_history(
    symbol: str,
    frequency: str = Query(default="daily", description="数据周期: daily/weekly/monthly/5min"),
    limit: int = Query(default=120, ge=10, le=500),
):
    """获取指数 K 线历史数据。"""
    freq_map = {
        "daily": FREQ_DAILY,
        "weekly": FREQ_WEEKLY,
        "monthly": FREQ_MONTHLY,
        "5min": FREQ_5MIN,
    }
    freq = freq_map.get(frequency, FREQ_DAILY)

    df = fetch_index_kline(symbol, freq, max_bars=limit * 2)
    name = INDICES.get(symbol, {}).get("name", symbol)

    items = _build_kline_items(df, limit)

    return IndexHistoryResponse(
        symbol=symbol,
        name=name,
        frequency=frequency,
        total=len(items),
        data=items,
    )


# ────────────────────────────────────────────
# 板块接口
# ────────────────────────────────────────────

@router.get("/sectors", response_model=SectorListResponse)
def get_sector_list():
    """获取所有可用板块列表。"""
    sectors = list_sectors()
    return SectorListResponse(sectors=[SectorListItem(**s) for s in sectors])


@router.get("/sector-categories", response_model=SectorCategoryResponse)
def get_sector_categories():
    """获取按类别分组的板块列表。"""
    categories = list_sector_categories()
    return SectorCategoryResponse(
        categories=[SectorCategory(category=c["category"], sectors=c["sectors"]) for c in categories]
    )


@router.get("/sector/{symbol}/history", response_model=SectorHistoryResponse)
def get_sector_history(
    symbol: str,
    frequency: str = Query(default="daily", description="数据周期: daily/weekly/monthly/5min"),
    limit: int = Query(default=120, ge=10, le=500),
):
    """获取板块指数 K 线历史数据。"""
    freq_map = {
        "daily": SECTOR_DAILY,
        "weekly": SECTOR_WEEKLY,
        "monthly": SECTOR_MONTHLY,
        "5min": SECTOR_5MIN,
    }
    freq = freq_map.get(frequency, SECTOR_DAILY)

    df = fetch_sector_kline(symbol, freq, max_bars=limit * 2)
    name = SECTORS.get(symbol, symbol)

    items = _build_kline_items(df, limit)

    return SectorHistoryResponse(
        symbol=symbol,
        name=name,
        frequency=frequency,
        total=len(items),
        data=items,
    )
