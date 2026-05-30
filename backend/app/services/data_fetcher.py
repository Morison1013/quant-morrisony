"""
数据获取服务层。

使用 pytdx（通达信行情协议）获取 A 股历史日 K 线数据。
设计为同步 + 异步生成器双模式，预留 SSE 实时推送管道。
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import AsyncGenerator

import pandas as pd
from pytdx.hq import TdxHq_API

# 通达信行情主站池（带自动 fallback）
TDX_SERVERS = [
    ("180.153.18.170", 7709),  # 最优
    ("218.75.126.9", 7709),
    ("60.12.136.250", 7709),
    ("115.238.56.198", 7709),
    ("115.238.90.165", 7709),
]

# pytdx 行情频率常量
FREQ_DAILY = 9    # 日线
FREQ_WEEKLY = 10  # 周线


def _detect_market(symbol: str) -> int:
    """
    判断股票市场：上海=1，深圳=0。

    Args:
        symbol: 纯数字股票代码

    Returns:
        market: 0=深圳, 1=上海
    """
    code = str(symbol).strip()
    # 上证指数: 6xxxxx, 科创板: 68xxxx → 上海
    if code.startswith(("6", "68")):
        return 1
    # 深圳: 0xxxxx, 3xxxxx (创业板)
    return 0


def _fetch_from_tdx(symbol: str, frequency: int = FREQ_DAILY, max_bars: int = 2400) -> pd.DataFrame:
    """
    从通达信服务器获取历史 K 线（每次 800 条，分页拉取）。

    Args:
        symbol: 股票代码（纯数字）
        frequency: K 线频率
        max_bars: 最大获取条数

    Returns:
        DataFrame with columns: date, open, close, high, low, volume
    """
    market = _detect_market(symbol)

    all_data = []
    batch_size = 800
    offset = 0

    for ip, port in TDX_SERVERS:
        api = TdxHq_API()
        try:
            if not api.connect(ip, port):
                continue

            while len(all_data) < max_bars:
                batch = api.get_security_bars(frequency, market, symbol, offset, batch_size)
                if not batch:
                    break
                all_data.extend(batch)
                offset += 1

            api.disconnect()
            if all_data:
                break
        except Exception:
            try:
                api.disconnect()
            except Exception:
                pass
            continue

    if not all_data:
        raise ConnectionError(
            f"无法连接任何通达信服务器获取 {symbol} 数据"
        )

    df = pd.DataFrame(all_data)
    df = df.rename(columns={"vol": "volume"})
    df["date"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("date").reset_index(drop=True)

    # 只保留策略需要的列
    df = df[["date", "open", "close", "high", "low", "volume"]].copy()

    # 去重：同一天多条记录只保留最新（最后一条）
    df = df.drop_duplicates(subset="date", keep="last")
    df = df.reset_index(drop=True)

    return df


def fetch_history_daily(symbol: str, period: str = "daily") -> pd.DataFrame:
    """
    获取指定股票的历史日 K 线数据（前复权，通达信默认返回前复权）。
    优先读取本地 SQLite 数据库（如果已刷新过）。

    Args:
        symbol: 股票代码（纯数字，如 "600519"）
        period: 数据周期，默认 "daily"

    Returns:
        包含 OHLCV 数据的 DataFrame，按日期升序排列
    """
    # 去除 sh/sz 前缀（兼容 AkShare 旧格式）
    code = str(symbol).lower().strip()
    if code.startswith(("sh", "sz")):
        code = code[2:]

    # 优先读本地 SQLite
    try:
        from app.services.db import load_kline, get_last_refresh

        if get_last_refresh():
            df = load_kline(code, limit=500)
            if df is not None and len(df) > 10:
                return df
    except Exception:
        pass  # SQLite 不可用，降级到 TDX

    return _fetch_from_tdx(code)


async def fetch_history_daily_stream(
    symbol: str, interval: float = 60.0
) -> AsyncGenerator[pd.DataFrame, None]:
    """
    异步生成器：周期性拉取最新数据，为 SSE 实时推送预留管道。

    Yields:
        最新的历史 DataFrame（每次调用会追加最新行情）
    """
    code = str(symbol).lower().strip()
    if code.startswith(("sh", "sz")):
        code = code[2:]

    while True:
        try:
            df = _fetch_from_tdx(code)
            yield df
        except Exception as e:
            print(f"[DataFetcher] Error fetching data: {e}")
        await asyncio.sleep(interval)


# ────────────────────────────────────────────
# 全市场股票列表获取
# ────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent.parent / "data"
STOCK_LIST_CACHE = DATA_DIR / "all_stocks.json"
CACHE_TTL = 300  # 5 分钟

# 上海 A 股代码模式（用于生成候选列表）
# 仅沪深主板：排除科创板(688)、创业板(300/301)、北交所
SH_PREFIXES = ["600", "601", "603", "605"]


def _fetch_sz_stocks_from_tdx() -> list[dict]:
    """
    从通达信服务器获取深圳 A 股列表（0xxxxx）。
    """
    # 优先使用 GTJAS 服务器（支持 get_security_list）
    servers = [
        ("sztdx.gtjas.com", 7709),
        ("shtdx.gtjas.com", 7709),
        ("jstdx.gtjas.com", 7709),
    ] + TDX_SERVERS

    for ip, port in servers:
        api = TdxHq_API()
        try:
            if not api.connect(ip, port):
                continue

            total_count = api.get_security_count(0)
            if not total_count:
                api.disconnect()
                continue

            stocks = []
            start = 0
            while start < total_count:
                result = api.get_security_list(0, start)
                if not result:
                    break
                for s in result:
                    code = s.get("code", "")
                    name = s.get("name", "")
                    # 6 位代码，仅沪深主板：00xxxx（主板），排除 30xxxx（创业板）、688（科创板）、北交所
                    if len(code) == 6 and code.startswith("00"):
                        stocks.append({"code": code, "name": name, "market": 0})
                start += len(result)

            api.disconnect()

            # 去重
            seen = set()
            unique = []
            for s in stocks:
                if s["code"] not in seen:
                    seen.add(s["code"])
                    unique.append(s)
            unique.sort(key=lambda x: x["code"])
            return unique
        except Exception:
            try:
                api.disconnect()
            except Exception:
                pass
            continue

    return []


def _generate_sh_stocks() -> list[dict]:
    """
    生成上海 A 股代码候选列表（基于已知前缀模式）。
    """
    stocks = []
    for prefix in SH_PREFIXES:
        for i in range(1000):
            code = f"{prefix}{i:03d}"
            stocks.append({"code": code, "name": "", "market": 1})
    return stocks


def _verify_and_filter_stocks(stocks: list[dict]) -> list[dict]:
    """
    验证股票列表有效性。
    - 深圳股票：保留（已从 TDX 获取，确认存在）
    - 上海股票：验证几只知名股票，通过后保留全部上海候选
    """
    # 深圳股票已经是从 TDX 获取的，确认存在
    sz_valid = [s for s in stocks if s["market"] == 0]

    # 上海股票：抽样验证几只主板股票
    sh_known = ["600519", "601398", "600036", "600276", "601888"]
    sh_valid_count = 0
    for code in sh_known:
        try:
            df = fetch_history_daily(code)
            if len(df) > 10:
                sh_valid_count += 1
        except Exception:
            pass

    # 如果至少 3 只知名股票能获取数据，保留全部上海候选
    if sh_valid_count >= 3:
        sh_valid = [s for s in stocks if s["market"] == 1]
    else:
        # 否则只保留验证通过的
        sh_valid = []

    return sz_valid + sh_valid


def get_all_stock_codes(refresh: bool = False) -> list[dict]:
    """
    获取全部 A 股代码列表（含名称）。

    Args:
        refresh: 是否强制刷新（忽略缓存）

    Returns:
        list[{"code": str, "name": str, "market": int}]
    """
    # 检查缓存
    if not refresh and STOCK_LIST_CACHE.exists():
        cache_age = time.time() - STOCK_LIST_CACHE.stat().st_mtime
        if cache_age < CACHE_TTL:
            with open(STOCK_LIST_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)

    # 从 TDX 获取深圳股票
    sz_stocks = _fetch_sz_stocks_from_tdx()
    print(f"[DataFetcher] Fetched {len(sz_stocks)} Shenzhen stocks from TDX")

    # 生成上海候选
    sh_stocks = _generate_sh_stocks()
    print(f"[DataFetcher] Generated {len(sh_stocks)} Shanghai candidates")

    # 合并
    all_stocks = sz_stocks + sh_stocks

    # 验证过滤
    all_stocks = _verify_and_filter_stocks(all_stocks)
    print(f"[DataFetcher] After validation: {len(all_stocks)} total stocks")

    # 保存缓存
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STOCK_LIST_CACHE, "w", encoding="utf-8") as f:
        json.dump(all_stocks, f, ensure_ascii=False)

    return all_stocks
