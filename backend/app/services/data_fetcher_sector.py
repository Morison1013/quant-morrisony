"""
板块指数数据获取服务。

通过 pytdx 获取通达信概念/行业板块指数数据。
"""

import pandas as pd
from pytdx.hq import TdxHq_API

from app.services.data_fetcher import TDX_SERVERS

# 通达信板块指数（880xxx，均为上海 market=1）
SECTORS = {
    # 行业板块
    "880355": "非银金融",
    "880360": "计算机",
    "880375": "白酒",
    "880380": "家用电器",
    "880382": "船舶制造",
    "880387": "环保",
    "880390": "高速公路",
    "880391": "铁路公路",
    "880392": "港口航运",
    "880393": "物流",
    "880406": "消费电子",
    "880408": "电池",
    "880410": "通信设备",
    "880413": "电力设备",
    "880418": "化工",
    "880420": "有色金属",
    "880421": "钢铁",
    "880423": "煤炭",
    "880424": "石油石化",
    "880425": "建筑材料",
    "880440": "光伏设备",
    "880513": "医药生物",

    # 概念/题材板块
    "880521": "CPO概念",
    "880530": "低空经济",
    "880534": "固态电池",
    "880535": "商业航天",
    "880536": "数据要素",
    "880537": "可控核聚变",
    "880538": "深海科技",
    "880539": "算力租赁",
    "880540": "铜缆高速连接",
    "880541": "华为概念",
    "880542": "小米概念",
    "880543": "苹果概念",
    "880544": "特斯拉概念",
    "880545": "英伟达概念",
    "880546": "机器人概念",
    "880547": "无人机概念",
    "880548": "虚拟现实",
    "880549": "元宇宙",
    "880550": "数字经济",
    "880551": "东数西算",
    "880552": "量子科技",
    "880553": "脑机接口",
    "880554": "合成生物",
    "880555": "创新药",
    "880556": "CXO概念",
    "880557": "医疗器械",
    "880558": "中药",
    "880592": "新能源车",
    "880599": "人形机器人",
    "880647": "AI芯片",
    "880478": "AI应用",
}

FREQ_5MIN = 8
FREQ_DAILY = 9
FREQ_WEEKLY = 10
FREQ_MONTHLY = 11


def fetch_sector_kline(symbol: str, frequency: int = FREQ_DAILY, max_bars: int = 2400) -> pd.DataFrame:
    """
    获取板块指数 K 线数据。

    Args:
        symbol: 板块代码（如 '880521'）
        frequency: K 线频率
        max_bars: 最大获取条数

    Returns:
        DataFrame with columns: date, open, close, high, low, volume, amount
    """
    if symbol not in SECTORS:
        raise ValueError(f"Unknown sector: {symbol}")

    all_data = []
    batch_size = 800
    offset = 0

    for ip, port in TDX_SERVERS:
        api = TdxHq_API()
        try:
            if not api.connect(ip, port):
                continue

            while len(all_data) < max_bars:
                batch = api.get_index_bars(frequency, 1, symbol, offset, batch_size)
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
        raise ConnectionError(f"无法获取板块 {symbol} 数据")

    df = pd.DataFrame(all_data)
    df = df.rename(columns={"vol": "volume"})
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    # 过滤掉无效日期
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    keep_cols = [c for c in ["date", "open", "close", "high", "low", "volume", "amount"] if c in df.columns]
    df = df[keep_cols].copy()

    return df


def fetch_sector_5min(symbol: str) -> pd.DataFrame:
    """获取板块最近 5 分钟 K 线数据。"""
    return fetch_sector_kline(symbol, FREQ_5MIN, max_bars=48)


def list_sectors() -> list[dict]:
    """返回所有可用板块列表。"""
    return [{"code": code, "name": name} for code, name in SECTORS.items()]


def list_sector_categories() -> list[dict]:
    """按类别返回板块列表。"""
    categories = {
        "行业板块": [],
        "科技/AI": [],
        "新能源": [],
        "大消费": [],
        "军工/高端制造": [],
        "医药": [],
        "概念题材": [],
    }

    for code, name in SECTORS.items():
        if code.startswith(("8803",)):
            categories["行业板块"].append({"code": code, "name": name})
        elif any(k in name for k in ["AI", "CPO", "算力", "数据", "数字", "东数", "量子", "脑机"]):
            categories["科技/AI"].append({"code": code, "name": name})
        elif any(k in name for k in ["电池", "光伏", "新能源车", "固态", "电力", "可控核"]):
            categories["新能源"].append({"code": code, "name": name})
        elif any(k in name for k in ["白酒", "食品", "家电", "旅游", "商业", "纺织"]):
            categories["大消费"].append({"code": code, "name": name})
        elif any(k in name for k in ["军工", "船舶", "商业航天", "低空", "无人机", "机器人", "人形", "深海"]):
            categories["军工/高端制造"].append({"code": code, "name": name})
        elif any(k in name for k in ["医药", "创新药", "CXO", "医疗器械", "中药", "合成"]):
            categories["医药"].append({"code": code, "name": name})
        else:
            categories["概念题材"].append({"code": code, "name": name})

    return [
        {"category": cat, "sectors": sectors}
        for cat, sectors in categories.items()
        if sectors
    ]
