"""
从通达信拉取全市场股票 5 分钟 K 线数据，入库 SQLite。

用法:
    python -m app.scripts.fetch_min5_kline [--limit 500] [--recent-only]

说明:
- 默认拉取全部 3200 只股票的 5min K 线
- 使用 --recent-only 只拉取最近有 K 线数据的股票
- 5min K 线用于：涨停时间分布、盘中分时分析
"""

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from pytdx.hq import TdxHq_API

from app.services.data_fetcher import TDX_SERVERS
from app.services.db import save_min5_kline, load_kline, get_conn, init_db


def _detect_market(symbol: str) -> int:
    if symbol.startswith(("6", "68")):
        return 1
    return 0


def fetch_min5_for_stock(code: str, max_bars: int = 800) -> int:
    """
    从通达信获取单只股票的 5 分钟 K 线数据。
    通达信 5min K 线最多返回 800 条（约 30 个交易日）。
    """
    market = _detect_market(code)
    FREQ_5MIN = 8

    all_data = []
    offset = 0
    batch_size = 800

    for ip, port in TDX_SERVERS:
        api = TdxHq_API()
        try:
            if not api.connect(ip, port):
                continue

            for _ in range(max_bars // batch_size + 1):
                batch = api.get_security_bars(FREQ_5MIN, market, code, offset, batch_size)
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
        return 0

    # 转 DataFrame
    records = []
    for d in all_data:
        records.append({
            "datetime": d.get("datetime", ""),
            "open": d.get("open", 0),
            "high": d.get("high", 0),
            "low": d.get("low", 0),
            "close": d.get("close", 0),
            "volume": d.get("vol", 0),
            "amount": d.get("amount", 0),
        })

    df = pd.DataFrame(records)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.dropna(subset=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    if df.empty:
        return 0

    save_min5_kline(code, df)
    return len(df)


def fetch_all_min5(max_bars: int = 800, recent_only: bool = True):
    """拉取全市场 5min K 线。"""
    init_db()

    # 获取股票列表
    conn = get_conn()
    if recent_only:
        # 只拉取有日线数据的股票
        df = pd.read_sql_query(
            "SELECT DISTINCT s.code, s.name FROM stocks s "
            "INNER JOIN daily_kline dk ON s.code = dk.code",
            conn,
        )
    else:
        df = pd.read_sql_query("SELECT code, name FROM stocks", conn)
    conn.close()

    codes = df["code"].tolist()
    names = dict(zip(df["code"], df["name"]))

    print(f"共 {len(codes)} 只股票需要拉取 5min K 线")
    print(f"每只最多 {max_bars} 条，总计约 {len(codes) * max_bars} 条")
    print()

    total_bars = 0
    success = 0
    failed = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_min5_for_stock, code, max_bars): code for code in codes}

        for i, future in enumerate(as_completed(futures)):
            code = futures[future]
            try:
                bars = future.result(timeout=30)
                if bars > 0:
                    total_bars += bars
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1

            if (i + 1) % 100 == 0 or i == len(codes) - 1:
                elapsed = time.time() - start
                speed = (i + 1) / elapsed
                print(f"  [{i+1}/{len(codes)}] 成功={success} 失败={failed} 总计={total_bars} 条 速度={speed:.1f}只/秒")

    elapsed = time.time() - start
    print()
    print(f"完成! 耗时 {elapsed:.0f}s")
    print(f"成功: {success}, 失败: {failed}")
    print(f"总 5min K 线条数: {total_bars}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=800, help="每只股票最大条数")
    parser.add_argument("--recent-only", action="store_true", help="只拉取有日线数据的股票")
    args = parser.parse_args()
    fetch_all_min5(max_bars=args.limit, recent_only=args.recent_only)
