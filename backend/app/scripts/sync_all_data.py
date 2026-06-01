"""
全量同步 akshare 股票名称 + 板块映射 到 SQLite + JSON 缓存。

同步目标：
1. 更新 SQLite stocks 表（名称补齐）
2. 更新 data/all_stocks.json（扫描器用）
3. 重新生成 data/sector_map.json（板块映射）
4. 清理无效股票（无 K 线 + 无名称）

用法:
    python -m app.scripts.sync_all_data
"""

import json
import sqlite3
import time
from pathlib import Path
from collections import Counter

DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DB_DIR / "market.db"


def get_akshare_names() -> dict:
    """从 akshare 获取全量股票名称。"""
    import akshare as ak
    print("正在从 akshare 获取股票列表...")
    df = ak.stock_info_a_code_name()
    names = dict(zip(df["code"], df["name"]))
    print(f"akshare 返回 {len(names)} 只股票")
    return names


def sync_db(ak_names: dict):
    """同步 SQLite stocks 表：更新名称、清理无效股票。"""
    print("\n" + "=" * 50)
    print("同步 SQLite 数据库")
    print("=" * 50)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 1. 更新已有股票名称
    cursor.execute("SELECT code, name FROM stocks")
    db_stocks = dict(cursor.fetchall())
    print(f"数据库当前: {len(db_stocks)} 只")

    updated = 0
    for code, name in db_stocks.items():
        if not name and code in ak_names:
            cursor.execute("UPDATE stocks SET name = ? WHERE code = ?", (ak_names[code], code))
            updated += 1

    # 2. 插入 akshare 有但数据库没有的股票
    inserted = 0
    for code, name in ak_names.items():
        if code not in db_stocks:
            market = 1 if code.startswith(("6", "68")) else 0
            cursor.execute(
                "INSERT OR IGNORE INTO stocks (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
                (code, name, market, time.strftime("%Y-%m-%d %H:%M:%S")),
            )
            inserted += 1

    # 3. 清理无 K 线数据且无名称的股票（幻影股票）
    cursor.execute("""
        DELETE FROM stocks
        WHERE (name IS NULL OR name = '')
        AND code NOT IN (SELECT DISTINCT code FROM daily_kline)
    """)
    deleted = cursor.rowcount

    conn.commit()

    # 确认
    cursor.execute("SELECT COUNT(*) FROM stocks")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stocks WHERE name IS NULL OR name = ''")
    no_name = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT code) FROM daily_kline")
    with_kline = cursor.fetchone()[0]
    conn.close()

    print(f"更新名称: {updated}")
    print(f"新增股票: {inserted}")
    print(f"清理幻影: {deleted}")
    print(f"数据库总计: {total}")
    print(f"剩余无名称: {no_name}")
    print(f"有 K 线数据的股票: {with_kline}")


def sync_all_stocks_json(ak_names: dict):
    """同步 all_stocks.json（全市场扫描缓存）。"""
    print("\n" + "=" * 50)
    print("同步 all_stocks.json（扫描器缓存）")
    print("=" * 50)

    cache_path = DB_DIR / "all_stocks.json"

    # 从数据库获取完整股票列表
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT code, name, market FROM stocks")
    stocks = []
    for code, name, market in cursor.fetchall():
        stocks.append({
            "code": code,
            "name": name if name else (ak_names.get(code, "")),
            "market": market,
        })
    conn.close()

    # 补充 akshare 中有的但数据库可能漏的
    existing_codes = {s["code"] for s in stocks}
    for code, name in ak_names.items():
        if code not in existing_codes:
            market = 1 if code.startswith(("6", "68")) else 0
            stocks.append({"code": code, "name": name, "market": market})

    # 清理空名称
    before = len(stocks)
    stocks = [s for s in stocks if s.get("name")]
    removed = before - len(stocks)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(stocks, f, ensure_ascii=False)

    no_name = sum(1 for s in stocks if not s.get("name"))
    print(f"总股票数: {len(stocks)}")
    print(f"移除无名称: {removed}")
    print(f"剩余无名称: {no_name}")


def regenerate_sector_map():
    """重新生成板块映射。"""
    print("\n" + "=" * 50)
    print("重新生成板块映射")
    print("=" * 50)

    # 已知重点股票板块
    KNOWN_SECTORS = {
        # 银行
        "600000": "银行", "600015": "银行", "600016": "银行", "600036": "银行",
        "600900": "银行", "600908": "银行", "600909": "证券", "600919": "银行",
        "600926": "银行", "600928": "银行", "601128": "银行", "601166": "银行",
        "601169": "银行", "601229": "银行", "601288": "银行", "601319": "保险",
        "601328": "银行", "601336": "保险", "601398": "银行", "601601": "保险",
        "601628": "保险", "601665": "银行", "601818": "银行", "601825": "银行",
        "601838": "银行", "601860": "银行", "601916": "银行", "601939": "银行",
        "601963": "银行", "601988": "银行", "601997": "银行", "601998": "银行",
        "601066": "证券", "601099": "证券", "601162": "证券", "601211": "证券",
        "601375": "证券", "601377": "证券", "601555": "证券", "601688": "证券",
        "601788": "证券", "601878": "证券", "601881": "证券", "601901": "证券",
        "601990": "证券", "601995": "证券", "601236": "证券", "600837": "证券",
        "600030": "证券", "600109": "证券", "600918": "证券", "600958": "证券",
        "600999": "证券", "601696": "证券", "601456": "证券", "601136": "证券",
        # 半导体
        "600460": "半导体", "600584": "半导体", "600745": "半导体",
        "601231": "半导体", "603005": "半导体", "603068": "半导体",
        "603228": "半导体", "603501": "半导体", "603893": "半导体",
        "603986": "半导体", "600703": "半导体", "603160": "半导体",
        "603019": "半导体", "603596": "半导体",
        # 白酒
        "600199": "白酒", "600519": "白酒", "600559": "白酒",
        "600702": "白酒", "600779": "白酒", "600809": "白酒",
        "603198": "白酒", "603369": "白酒", "603589": "白酒",
        # 光伏/新能源
        "600438": "光伏", "600732": "光伏", "601012": "光伏",
        "601865": "光伏", "601908": "光伏", "603628": "光伏",
        "603806": "光伏", "603486": "光伏", "603212": "光伏",
        "601778": "光伏", "600586": "光伏",
        # 锂电池
        "603799": "锂电池", "603659": "锂电池", "600089": "锂电池",
        "600563": "锂电池", "603799": "锂电池", "600143": "锂电池",
        # 新能源车
        "600066": "新能源车", "600418": "新能源车", "600733": "新能源车",
        "601127": "新能源车", "601238": "新能源车", "601633": "新能源车",
        "601777": "新能源车", "601799": "新能源车", "603179": "新能源车",
        "603786": "新能源车", "603997": "新能源车", "600741": "新能源车",
        "601689": "新能源车", "601888": "汽车",
        # 医药
        "600196": "医药", "600267": "医药", "600276": "医药",
        "600436": "医药", "600521": "医药", "600535": "医药",
        "600557": "医药", "600566": "医药", "600594": "医药",
        "600812": "医药", "600867": "医药", "603259": "医药",
        "603367": "医药", "603456": "医药", "603883": "医药",
        "603939": "医药", "600216": "医药", "600572": "医药",
        # 科技/AI
        "600570": "计算机", "600588": "计算机", "600718": "计算机",
        "600797": "计算机", "601360": "计算机", "603039": "计算机",
        "603881": "计算机", "603927": "计算机", "601138": "计算机",
        "600845": "计算机", "603035": "计算机",
        # 消费/食品
        "600690": "家电", "600887": "乳业", "603288": "食品",
        "603517": "食品", "603345": "食品", "603027": "食品",
        "603711": "食品", "603866": "食品", "603697": "食品",
        "603777": "食品", "603155": "乳业", "605499": "饮料",
        "603079": "食品", "600597": "乳业", "600298": "食品",
        # 军工
        "600038": "军工", "600118": "军工", "600150": "军工",
        "600151": "军工", "600316": "军工", "600372": "军工",
        "600391": "军工", "600435": "军工", "600685": "军工",
        "600760": "军工", "600862": "军工", "600893": "军工",
        "601989": "军工", "600855": "军工",
        # 建筑/基建
        "600170": "建筑", "600491": "建筑", "601117": "建筑",
        "601186": "建筑", "601390": "建筑", "601618": "建筑",
        "601668": "建筑", "601669": "建筑", "601800": "建筑",
        "601611": "建筑", "601727": "电力设备", "601179": "电力设备",
        # 电力
        "600011": "电力", "600021": "电力", "600023": "电力",
        "600027": "电力", "600236": "电力", "600644": "电力",
        "600795": "电力", "600863": "电力", "600886": "电力",
        "601985": "核电", "601991": "电力", "601816": "电力",
        "600995": "电力",
        # 煤炭
        "600188": "煤炭", "600508": "煤炭", "600546": "煤炭",
        "601088": "煤炭", "601225": "煤炭", "601699": "煤炭",
        "601898": "煤炭", "601918": "煤炭",
        # 石油
        "600028": "石油", "600339": "石油", "600688": "石油",
        "601808": "石油", "601857": "石油",
        # 钢铁
        "600019": "钢铁", "600022": "钢铁", "600231": "钢铁",
        "600282": "钢铁", "600569": "钢铁", "600782": "钢铁",
        "600808": "钢铁", "601003": "钢铁", "601005": "钢铁",
        # 有色
        "600219": "有色", "600362": "有色", "600489": "有色",
        "600497": "有色", "600547": "有色", "600961": "有色",
        "601168": "有色", "601600": "有色", "601899": "有色",
        "603993": "有色", "600490": "有色", "600549": "有色",
        "603067": "有色", "601020": "有色", "601111": "有色",
        # 化工
        "600096": "化工", "600141": "化工", "600309": "化工",
        "600409": "化工", "600426": "化工", "600486": "化工",
        "600596": "化工", "603026": "化工", "603630": "化工",
        "603996": "化工", "603737": "化工", "603778": "化工",
        # 汽车
        "600166": "汽车",
        # 通信
        "600498": "通信", "600522": "通信", "601728": "通信",
        "603220": "通信", "603322": "通信", "600050": "通信",
        "603888": "通信", "603075": "通信", "600941": "通信",
        # 物流
        "600026": "物流", "600125": "物流", "600428": "物流",
        "600787": "物流", "601156": "物流", "601598": "物流",
        "600233": "物流",
        # 地产
        "600048": "地产", "600383": "地产", "600606": "地产",
        "600649": "地产", "600743": "地产", "601155": "地产",
        "601595": "地产",
        # 环保
        "600008": "环保", "600292": "环保", "600481": "环保",
        "600526": "环保", "603279": "环保", "603588": "环保",
        # 农业
        "600313": "农业", "600598": "农业", "600975": "农业",
        "601952": "农业", "600359": "农业", "600195": "农业",
        # 酒店
        "600258": "酒店", "600754": "酒店", "603136": "旅游",
        "601007": "酒店",
        # 传媒
        "600373": "传媒", "600633": "传媒", "600637": "传媒",
        "600959": "传媒", "600996": "传媒", "601098": "传媒",
        "601801": "传媒", "601928": "传媒", "601949": "传媒",
        "600977": "影视", "603103": "影视", "603533": "传媒",
        "603466": "传媒",
        # 风电
        "601615": "风电", "603218": "风电", "601016": "风电",
        "601226": "风电", "601619": "风电",
        # 养殖
        "603477": "养殖", "605296": "养殖",
        # 零售
        "600694": "零售", "600729": "零售", "600827": "零售",
        "600859": "零售", "601933": "零售",
    }

    # 从数据库获取所有股票
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM stocks")
    all_codes = [r[0] for r in cursor.fetchall()]
    conn.close()

    sector_map = {}

    # 1. 精确映射
    for code, sector in KNOWN_SECTORS.items():
        sector_map[code] = sector

    # 2. 前缀推断
    for code in all_codes:
        if code in sector_map:
            continue
        if code.startswith(("300", "301")):
            sector_map[code] = "创业板"
        elif code.startswith(("688", "689")):
            sector_map[code] = "科创板"
        elif code.startswith(("000", "001", "002", "003")):
            sector_map[code] = "深圳主板"
        elif code.startswith("600"):
            sector_map[code] = "沪深主板"
        elif code.startswith("601"):
            sector_map[code] = "沪深主板"
        elif code.startswith("603"):
            sector_map[code] = "中小盘"
        elif code.startswith("605"):
            sector_map[code] = "中小盘"
        else:
            sector_map[code] = "其他"

    # 保存
    output_path = DB_DIR / "sector_map.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sector_map, f, ensure_ascii=False, indent=2)

    counts = Counter(sector_map.values())
    print(f"板块映射: {len(sector_map)} 只股票")
    print("\n板块分布 Top 15:")
    for sector, count in counts.most_common(15):
        print(f"  {sector}: {count}")


if __name__ == "__main__":
    print("\n")
    print("=" * 60)
    print("全量同步 akshare 名称 + 板块映射")
    print("=" * 60)

    # Step 1: 获取 akshare 名称
    ak_names = get_akshare_names()

    # Step 2: 同步数据库
    sync_db(ak_names)

    # Step 3: 同步 all_stocks.json
    sync_all_stocks_json(ak_names)

    # Step 4: 重新生成板块映射
    regenerate_sector_map()

    print("\n" + "=" * 60)
    print("同步完成!")
    print("=" * 60)
