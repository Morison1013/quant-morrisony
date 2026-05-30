"""
每日数据刷新脚本。

每天收盘后运行一次（15:30），将全市场最新行情写入本地 SQLite。
之后扫描和查询直接读本地，速度提升 20×+。

用法：
    python scripts/refresh_daily.py          # 全量刷新
    python scripts/refresh_daily.py --force  # 强制刷新（忽略已有数据）
"""

import argparse
import sys
import time
from pathlib import Path

# 确保能导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from pytdx.hq import TdxHq_API

from app.services.data_fetcher import TDX_SERVERS, get_all_stock_codes, _detect_market
from app.services.db import (
    init_db,
    save_stock_list,
    save_kline,
    get_last_refresh,
    log_refresh,
    get_db_stats,
)


def refresh_one(api: TdxHq_API, code: str, market: int) -> bool:
    """拉取单只股票数据并写入数据库。"""
    try:
        data = api.get_security_bars(9, market, code, 0, 250)  # 约一年数据
        if not data or len(data) < 60:
            return False

        import pandas as pd

        records = []
        for d in data:
            records.append({
                "date": f"{d['year']:04d}-{d['month']:02d}-{d['day']:02d}",
                "open": d["open"],
                "high": d["high"],
                "low": d["low"],
                "close": d["close"],
                "volume": d["vol"],
                "amount": d.get("amount", 0),
            })

        df = pd.DataFrame(records)
        save_kline(code, df)
        return True
    except Exception:
        return False


def main(force: bool = False):
    init_db()

    print("=" * 60)
    print("Quant_Morrisony — 每日数据刷新")
    print("=" * 60)

    last = get_last_refresh()
    if last and not force:
        print(f"上次刷新: {last}")
        print("（使用 --force 强制刷新）")

    # 获取股票列表
    all_stocks = get_all_stock_codes(refresh=True)
    print(f"\n股票总数: {len(all_stocks)}")
    print(f"沪深主板: {sum(1 for s in all_stocks if s['market'] == 0)} 深圳 + {sum(1 for s in all_stocks if s['market'] == 1)} 上海")

    # 保存股票列表
    save_stock_list(all_stocks)

    # 连接 TDX
    server = TDX_SERVERS[0]
    api = TdxHq_API()
    if not api.connect(server[0], server[1]):
        print(f"\n⚠️ 无法连接 {server[0]}:{server[1]}，尝试其他服务器...")
        for ip, port in TDX_SERVERS[1:]:
            if api.connect(ip, port):
                print(f"  → 已连接 {ip}:{port}")
                server = (ip, port)
                break
        else:
            print("❌ 无法连接任何通达信服务器")
            return

    print(f"\n数据源: {server[0]}:{server[1]}")
    print("开始刷新...\n")

    started = time.strftime("%Y-%m-%d %H:%M:%S")
    start_time = time.time()
    success = 0
    failed = 0
    total = len(all_stocks)

    for i, stock in enumerate(all_stocks):
        code = stock["code"]
        market = stock["market"]

        ok = refresh_one(api, code, market)
        if ok:
            success += 1
        else:
            failed += 1

        # 每 500 只打印一次进度
        if (i + 1) % 500 == 0 or i + 1 == total:
            elapsed = time.time() - start_time
            speed = (i + 1) / elapsed
            remaining = (total - i - 1) / speed if speed > 0 else 0
            print(f"  [{i + 1:>5}/{total}] 成功={success:>4} 失败={failed:>4} 速度={speed:.0f}只/秒 预计剩余={remaining:.0f}s")

    api.disconnect()

    elapsed = time.time() - start_time
    finished = time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'=' * 60}")
    print(f"刷新完成!")
    print(f"  总计: {total} 只")
    print(f"  成功: {success}")
    print(f"  失败: {failed}")
    print(f"  耗时: {elapsed:.0f}s ({elapsed / 60:.1f}min)")

    # 记录日志
    log_refresh(started, finished, total, success, failed, elapsed)

    # 显示统计
    stats = get_db_stats()
    print(f"\n数据库统计:")
    print(f"  股票数: {stats['stock_count']}")
    print(f"  K线条数: {stats['kline_count']:,}")
    print(f"  日期范围: {stats['date_from']} ~ {stats['date_to']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="每日数据刷新脚本")
    parser.add_argument("--force", action="store_true", help="强制刷新（忽略已有数据）")
    args = parser.parse_args()
    main(force=args.force)
