#!/usr/bin/env python3
"""通过 akshare 获取申万行业分类数据"""

import json
import time
import akshare as ak
from pathlib import Path
from collections import Counter, defaultdict

SECTOR_MAP_PATH = Path(r"C:\Users\morrison\Quant_Morrisony\backend\data\sector_map.json")

# 申万行业分类（2021版）- 主要行业
SW_INDUSTRIES = [
    "银行", "证券", "保险", "房地产开发", "建筑装饰", "建筑材料",
    "钢铁", "有色金属", "煤炭", "石油石化", "基础化工", "化学制品",
    "电力", "水务", "燃气", "环保",
    "半导体", "电子", "计算机", "通信", "传媒", "互联网",
    "汽车", "汽车零部件", "交通运输", "物流",
    "机械设备", "电气设备", "仪器仪表", "通用设备", "专用设备",
    "医药生物", "医疗服务", "医疗器械", "中药", "化学制药",
    "食品加工", "饮料乳品", "白酒", "啤酒", "调味品",
    "农林牧渔", "农产品加工", "饲料", "养殖业",
    "商贸零售", "纺织服装", "轻工制造", "家用电器", "家居用品",
    "国防军工", "航天航空", "兵器兵装",
    "公用事业", "环保工程", "园林工程",
    "教育", "旅游酒店", "餐饮", "体育", "娱乐",
    "银行", "非银金融", "多元金融",
    "新能源", "光伏", "锂电池", "风电", "储能", "新能源汽车",
    "机器人", "人工智能", "大数据", "云计算", "物联网",
    "稀土", "锂矿", "钴", "镍", "石墨烯",
    "美容护理", "宠物", "母婴用品",
    "房地产服务", "物业管理",
    "水泥", "玻璃", "陶瓷",
    "造纸", "包装印刷",
    "中药", "生物制品", "CXO",
    "医疗器械", "医疗耗材", "诊断服务",
    "半导体设备", "半导体材料", "芯片", "集成电路",
    "消费电子", "智能穿戴", "VRAR",
    "MiniLED", "LED", "显示面板", "光学光电子",
    "传感器", "连接器", "PCB",
    "电线电缆", "电机", "变压器",
    "工业母机", "数控机床", "激光设备",
    "矿山机械", "工程机械", "农业机械",
    "包装设备", "印刷设备",
    "轮胎", "橡胶", "塑料制品",
    "合成纤维", "化纤", "氨纶", "涤纶",
    "农药", "化肥", "种子",
    "水产养殖", "畜禽养殖", "种植",
    "白酒", "啤酒", "黄酒", "葡萄酒",
    "软饮料", "茶饮料", "果汁", "乳制品",
    "休闲食品", "烘焙", "糖果", "坚果",
    "调味发酵品", "酱油", "醋",
    "男装", "女装", "童装", "运动服装", "鞋帽",
    "家纺", "床上用品", "毛巾",
    "黄金", "珠宝", "钻石", "首饰",
    "零售", "百货", "超市", "便利店", "电商",
    "酒店", "景区", "旅行社", "邮轮",
    "影视", "动漫", "游戏", "音乐", "直播",
    "出版", "图书", "报纸", "杂志",
    "广告", "营销", "公关",
    "体育用品", "健身器材", "户外装备",
    "养老", "康复", "护理",
    "幼儿园", "K12教育", "职业教育", "在线教育",
    "殡葬服务", "墓地",
    "电线", "电缆", "光缆",
    "铁矿石", "铜", "铝", "锌", "铅", "镍", "锡",
    "稀土永磁", "稀土发光", "稀土催化",
    "氟化工", "氯碱化工", "纯碱", "磷化工",
    "钛白粉", "MDI", "TDI", "DMF",
    "农药中间体", "染料中间体",
    "铅酸电池", "镍氢电池", "锂电池", "钠离子电池",
    "正极材料", "负极材料", "电解液", "隔膜",
    "铜箔", "铝箔", "结构件",
    "整车制造", "乘用车", "商用车", "客车", "货车",
    "发动机", "变速箱", "底盘", "车身",
    "轮胎", "玻璃", "座椅", "内饰",
    "电池管理系统", "电机控制器", "充电桩",
    "智能座舱", "自动驾驶", "车联网",
    "光伏组件", "光伏电池", "光伏玻璃", "逆变器",
    "硅料", "硅片", "银浆", "铝边框",
    "风电整机", "叶片", "塔筒", "齿轮箱",
    "海缆", "锚链", "安装船",
    "水电", "火电", "核电", "生物质发电",
    "储能电池", "储能变流器", "能量管理系统",
    "特高压", "智能电网", "配电网",
    "燃气发电", "分布式能源",
    "污水处理", "垃圾处理", "大气治理",
    "环境监测", "环保设备",
    "碳交易", "碳中和", "节能减排",
    "数据中心", "服务器", "存储", "网络设备",
    "云计算", "边缘计算", "量子计算",
    "网络安全", "信息安全", "数据安全",
    "软件开发", "IT服务", "系统集成",
    "游戏开发", "游戏运营", "游戏引擎",
    "视频平台", "短视频", "直播平台",
    "社交网络", "即时通讯", "门户网站",
    "电商平台", "在线支付", "物流配送",
    "在线教育平台", "教育软件",
    "医疗信息化", "医院管理系统",
    "金融科技", "数字货币", "区块链",
    "智能家居", "智能音箱", "智能门锁",
    "智能家电", "扫地机器人", "空气净化器",
    "智能照明", "智能开关", "智能窗帘",
    "无人机", "服务机器人", "工业机器人",
    "数控系统", "伺服电机", "减速器",
    "机器视觉", "传感器", "控制器",
]

def main():
    # 加载现有数据
    with open(SECTOR_MAP_PATH, "r", encoding="utf-8") as f:
        sector_map = json.load(f)

    print(f"现有 sector_map: {len(sector_map)} 条")

    broad_tags = ['深圳主板', '沪市主板', '沪深主板', '中小盘', '创业板', '科创板', '北交所', '主板']

    # 获取需要更新的股票代码（宽基标签）
    need_update = {code: tag for code, tag in sector_map.items() if tag in broad_tags}
    print(f"需要更新的股票: {len(need_update)} 条")

    # 获取申万行业分类列表
    print("\n获取申万行业分类列表...")
    try:
        # 获取行业板块列表
        industry_list = ak.stock_board_industry_name_em()
        print(f"获取到 {len(industry_list)} 个行业板块")

        # 逐个获取每个行业的股票
        new_sector_map = {}
        success_count = 0
        fail_count = 0

        for idx, row in industry_list.iterrows():
            industry_name = row.get('板块名称', '')
            if not industry_name:
                continue

            # 排除宽基标签
            if industry_name in broad_tags:
                continue

            try:
                # 获取该行业的股票列表
                stocks = ak.stock_board_industry_cons_em(symbol=industry_name)
                for _, stock in stocks.iterrows():
                    code = str(stock.get('代码', '')).zfill(6)
                    if code and len(code) == 6 and code.isdigit():
                        if code in need_update:
                            new_sector_map[code] = industry_name
                            success_count += 1

                print(f"  {industry_name}: {len(stocks)} 只股票")
                time.sleep(0.15)  # 控制请求频率

            except Exception as e:
                fail_count += 1
                if fail_count % 10 == 0:
                    print(f"  获取失败 {fail_count} 次...")
                time.sleep(0.5)
                continue

        print(f"\n成功获取 {success_count} 只股票的行业数据")

        # 更新 sector_map
        for code, industry in new_sector_map.items():
            sector_map[code] = industry

        # 保存
        with open(SECTOR_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(sector_map, f, ensure_ascii=False, indent=2)

        print(f"\n保存完成！新的 sector_map 共 {len(sector_map)} 条")

        # 统计新的标签分布
        counter = Counter(sector_map.values())
        print("\n新的标签分布（前30个）：")
        for tag, count in counter.most_common(30):
            print(f"  {tag}: {count}")

        # 检查剩余的宽基标签
        remaining_broad = sum(count for tag, count in counter.items() if tag in broad_tags)
        print(f"\n剩余宽基标签: {remaining_broad}")

    except Exception as e:
        print(f"获取行业数据失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()