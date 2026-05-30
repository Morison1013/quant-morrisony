"""
数据看板 Pydantic Schema。
"""

from pydantic import BaseModel
from typing import Optional


class IndexKLineItem(BaseModel):
    """指数/板块 K 线数据。"""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float
    amount: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma30: Optional[float] = None
    ma55: Optional[float] = None
    ma60: Optional[float] = None


class IndexListItem(BaseModel):
    code: str
    name: str
    market: int


class IndexListResponse(BaseModel):
    indices: list[IndexListItem]


class IndexHistoryResponse(BaseModel):
    symbol: str
    name: str
    frequency: str
    total: int
    data: list[IndexKLineItem]


# ────────────────────────────────────────────
# 板块 Schema
# ────────────────────────────────────────────

class SectorListItem(BaseModel):
    code: str
    name: str


class SectorListResponse(BaseModel):
    sectors: list[SectorListItem]


class SectorCategory(BaseModel):
    category: str
    sectors: list[SectorListItem]


class SectorCategoryResponse(BaseModel):
    categories: list[SectorCategory]


class SectorHistoryResponse(BaseModel):
    symbol: str
    name: str
    frequency: str
    total: int
    data: list[IndexKLineItem]
