#!/usr/bin/env python3
"""批量获取股票名称并更新数据库"""

import sqlite3
import urllib.request
import urllib.parse
import time
import re

DB_PATH = r"C:\Users\morrison\Quant_Morrisony\backend\data\market.db"

def get_stock_names_sina(codes):
    """通过新浪财经API获取股票名称"""
    # 沪市股票代码前加 sh
    symbols = [f"sh{code}" for code in codes]
    url = f"http://hq.sinajs.cn/list={','.join(symbols)}"

    try:
        req = urllib.request.Request(url)
        req.add_header('Referer', 'http://finance.sina.com.cn')
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('gbk')

        # 解析返回数据
        # 格式: var hq_str_sh600000="浦发银行,..."
        result = {}
        for line in content.strip().split('\n'):
            if not line.strip():
                continue
            match = re.match(r'var hq_str_(sh\d+)="(.*)"', line.strip())
            if match:
                symbol = match.group(1)
                data = match.group(2)
                if data:
                    parts = data.split(',')
                    if len(parts) >= 1:
                        code = symbol[2:]  # 去掉 sh 前缀
                        result[code] = parts[0]  # 股票名称
        return result
    except Exception as e:
        print(f"请求失败: {e}")
        return {}

def get_stock_names_eastmoney(codes):
    """通过东方财富API获取股票名称（备用）"""
    # 东方财富API可以批量查询
    secids = [f"1.{code}" for code in codes]  # 1 表示沪市
    url = f"https://push2.eastmoney.com/api/qt/ulist.np?fltt=2&secids={','.join(secids)}&fields=f12,f14"

    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        result = {}
        if data.get('data', {}).get('diff'):
            for item in data['data']['diff']:
                code = item.get('f12', '')
                name = item.get('f14', '')
                if code and name:
                    result[code] = name
        return result
    except Exception as e:
        print(f"东方财富请求失败: {e}")
        return {}

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取缺少名称的股票代码
    cursor.execute("SELECT code FROM stocks WHERE name IS NULL OR name = ''")
    missing_codes = [row[0] for row in cursor.fetchall()]

    print(f"共有 {len(missing_codes)} 只股票缺少名称")

    # 批量获取，每次500只
    batch_size = 500
    total_updated = 0

    for i in range(0, len(missing_codes), batch_size):
        batch = missing_codes[i:i+batch_size]
        print(f"正在处理 {i+1}-{min(i+batch_size, len(missing_codes))} / {len(missing_codes)}...")

        names = get_stock_names_sina(batch)

        if names:
            # 更新数据库
            for code, name in names.items():
                try:
                    cursor.execute("UPDATE stocks SET name = ? WHERE code = ?", (name, code))
                    total_updated += 1
                except Exception as e:
                    print(f"更新失败 {code}: {e}")

            conn.commit()
            print(f"  成功获取 {len(names)} 只股票名称")

        time.sleep(0.3)  # 避免请求过快

    conn.close()
    print(f"\n完成！共更新 {total_updated} 只股票名称")

if __name__ == "__main__":
    main()