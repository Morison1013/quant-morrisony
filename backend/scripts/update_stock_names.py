#!/usr/bin/env python
"""
股票名称更新脚本 - 腾讯财经数据源。

批量查询腾讯财经接口获取股票名称，更新数据库。

使用方法：
    python scripts/update_stock_names.py
"""

import sys
import time
import re
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3


def get_all_codes_from_db():
    """
    从数据库获取所有股票代码。
    """
    db_path = Path(__file__).parent.parent / "data" / "market.db"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT code, market FROM stocks")
    codes = cursor.fetchall()
    conn.close()

    return codes


def get_names_from_tencent(codes: list, batch_size: int = 500):
    """
    从腾讯财经批量获取股票名称。

    Args:
        codes: [(code, market), ...]
        batch_size: 每批查询数量

    Returns:
        dict: {code: name}
    """
    print(f"正在从腾讯财经获取股票名称，共 {len(codes)} 只...")

    stock_map = {}

    # 分批查询
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]

        # 构建查询字符串: sh600000,sz000001,...
        query_codes = []
        for code, market in batch:
            prefix = "sh" if market == 1 or code.startswith('6') else "sz"
            query_codes.append(f"{prefix}{code}")

        url = f"http://qt.gtimg.cn/q={','.join(query_codes)}"

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read().decode('gbk')

                # 解析返回数据
                # 格式: v_sh600000="1~股票名称~600000~..."
                for line in data.split('\n'):
                    if not line.strip():
                        continue

                    # 提取代码和名称
                    match = re.match(r'v_(sh|sz)(\d+)="([^"]*)"', line)
                    if match:
                        prefix = match.group(1)
                        code = match.group(2)
                        content = match.group(3)

                        # 解析内容获取名称（第二个字段）
                        parts = content.split('~')
                        if len(parts) >= 2:
                            name = parts[1]
                            if name and name != '0':
                                stock_map[code] = name

                print(f"  第 {i//batch_size + 1} 批: {len(batch)} 只 -> 已获取 {len(stock_map)} 只名称")

        except Exception as e:
            print(f"  第 {i//batch_size + 1} 批请求失败: {e}")

        # 避免请求过快
        time.sleep(0.3)

    return stock_map


def update_database(stock_map: dict):
    """
    更新 SQLite 数据库中的股票名称。
    """
    db_path = Path(__file__).parent.parent / "data" / "market.db"

    print(f"\n正在更新数据库...")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    updated = 0

    for code, name in stock_map.items():
        updated_at = time.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("UPDATE stocks SET name = ?, updated_at = ? WHERE code = ?",
                       (name, updated_at, code))

        if cursor.rowcount > 0:
            updated += 1

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM stocks WHERE name IS NOT NULL AND name != ''")
    has_name = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stocks")
    total = cursor.fetchone()[0]

    conn.close()

    print(f"  更新: {updated} 条")
    print(f"  总计: {total} 只股票，有名称: {has_name} 只")


def update_json_cache(stock_map: dict):
    """
    更新 all_stocks.json 缓存文件。
    """
    import json

    cache_path = Path(__file__).parent.parent / "data" / "all_stocks.json"

    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = []

    existing_map = {s["code"]: s for s in existing}

    for code, name in stock_map.items():
        if code in existing_map:
            existing_map[code]["name"] = name

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False)

    print(f"\n已更新缓存: {cache_path}")


def main():
    print("=" * 50)
    print("股票名称更新脚本 (腾讯财经数据源)")
    print("=" * 50)

    # 1. 获取数据库中的所有股票代码
    codes = get_all_codes_from_db()
    print(f"数据库中共有 {len(codes)} 只股票")

    if not codes:
        print("数据库中没有股票数据")
        return

    # 2. 从腾讯财经获取名称
    stock_map = get_names_from_tencent(codes)

    print(f"\n成功获取 {len(stock_map)} 只股票名称")

    if not stock_map:
        print("无法获取股票名称")
        return

    # 3. 更新数据库
    update_database(stock_map)

    # 4. 更新缓存
    update_json_cache(stock_map)

    print("\n[OK] 股票名称更新完成！")


if __name__ == "__main__":
    main()