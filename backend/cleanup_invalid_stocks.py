#!/usr/bin/env python3
"""清理无效股票代码"""

import sqlite3

DB_PATH = r"C:\Users\morrison\Quant_Morrisony\backend\data\market.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 统计无效股票
    cursor.execute("SELECT COUNT(*) FROM stocks WHERE name IS NULL OR name = ''")
    invalid_stocks = cursor.fetchone()[0]

    print(f"共有 {invalid_stocks} 只无效股票代码")

    # 检查这些股票是否有 K 线数据
    cursor.execute("""
        SELECT COUNT(*) FROM daily_kline dk
        WHERE EXISTS (
            SELECT 1 FROM stocks s
            WHERE s.code = dk.code AND (s.name IS NULL OR s.name = '')
        )
    """)
    invalid_klines = cursor.fetchone()[0]

    print(f"无效股票相关的日K线数据: {invalid_klines} 条")

    cursor.execute("""
        SELECT COUNT(*) FROM min5_kline mk
        WHERE EXISTS (
            SELECT 1 FROM stocks s
            WHERE s.code = mk.code AND (s.name IS NULL OR s.name = '')
        )
    """)
    invalid_min5 = cursor.fetchone()[0]

    print(f"无效股票相关的5分钟K线数据: {invalid_min5} 条")

    # 删除无效股票的 K 线数据
    print("\n正在清理无效数据...")

    cursor.execute("""
        DELETE FROM daily_kline
        WHERE EXISTS (
            SELECT 1 FROM stocks s
            WHERE s.code = daily_kline.code AND (s.name IS NULL OR s.name = '')
        )
    """)
    print(f"删除日K线数据: {cursor.rowcount} 条")

    cursor.execute("""
        DELETE FROM min5_kline
        WHERE EXISTS (
            SELECT 1 FROM stocks s
            WHERE s.code = min5_kline.code AND (s.name IS NULL OR s.name = '')
        )
    """)
    print(f"删除5分钟K线数据: {cursor.rowcount} 条")

    # 删除无效股票代码
    cursor.execute("DELETE FROM stocks WHERE name IS NULL OR name = ''")
    print(f"删除无效股票代码: {cursor.rowcount} 条")

    conn.commit()

    # 统计清理后的数据
    cursor.execute("SELECT COUNT(*) FROM stocks")
    total_stocks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM daily_kline")
    total_daily = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM min5_kline")
    total_min5 = cursor.fetchone()[0]

    conn.close()

    print(f"\n清理完成！")
    print(f"剩余股票: {total_stocks} 只")
    print(f"剩余日K线: {total_daily} 条")
    print(f"剩余5分钟K线: {total_min5} 条")

if __name__ == "__main__":
    main()