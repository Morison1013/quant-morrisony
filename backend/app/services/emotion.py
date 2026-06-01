"""
打板情绪监控服务（日线版 + 5min 扩展）。

基于本地 SQLite 的 daily_kline + min5_kline 数据计算。
数据在每日 12:00（午间复盘）和 14:30（尾盘复盘）拉取。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from app.services.db import (
    DB_PATH, get_conn, load_stock_list,
    save_emotion_snapshot, load_emotion_history, load_min5_kline,
)

# ────────────────────────────────────────────
# 板块映射
# ────────────────────────────────────────────

SECTOR_MAP_PATH = DB_PATH.parent / "sector_map.json"

def _load_sector_map() -> dict:
    if SECTOR_MAP_PATH.exists():
        try:
            with open(SECTOR_MAP_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

_SECTOR_MAP_CACHE: dict = {}

def _get_sector(code: str) -> str:
    global _SECTOR_MAP_CACHE
    if not _SECTOR_MAP_CACHE:
        _SECTOR_MAP_CACHE = _load_sector_map()
    return _SECTOR_MAP_CACHE.get(code, "—")

# ────────────────────────────────────────────
# 涨跌停判定
# ────────────────────────────────────────────

LIMIT_UP_THRESHOLD = 9.8
LIMIT_DOWN_THRESHOLD = -9.8
MAIN_BOARD_PREFIXES = ("000", "001", "002", "003", "600", "601", "603", "605")


def _is_main_board(code: str) -> bool:
    return code.startswith(MAIN_BOARD_PREFIXES)


def _calc_change_pct(close: float, prev_close: float) -> float:
    if prev_close <= 0:
        return 0.0
    return ((close - prev_close) / prev_close) * 100


def _get_prev_trading_day(df: pd.DataFrame, current_date: str) -> Optional[str]:
    dates = sorted(df["date"].unique(), reverse=True)
    for i, d in enumerate(dates):
        if str(d.date()) == current_date and i + 1 < len(dates):
            return str(dates[i + 1].date())
    return None


# ────────────────────────────────────────────
# 核心计算
# ────────────────────────────────────────────

def compute_emotion_data() -> dict:
    """计算全部情绪指标。"""
    conn = get_conn()
    if conn is None:
        return _empty_result()

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM daily_kline")
        row = cursor.fetchone()
        latest_date = row[0] if row and row[0] else None
        if not latest_date:
            return _empty_result()

        # 获取最近 10 天数据
        df = pd.read_sql_query(
            """
            SELECT code, date, open, high, low, close, volume, amount
            FROM daily_kline
            WHERE date >= (
                SELECT DISTINCT date FROM daily_kline ORDER BY date DESC LIMIT 1 OFFSET ?
            )
            ORDER BY code, date
            """,
            conn,
            params=(9,),
        )
        if df.empty:
            return _empty_result()

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(["code", "date"]).reset_index(drop=True)

        # 计算涨跌幅
        df["prev_close"] = df.groupby("code")["close"].shift(1)
        df["change_pct"] = df.apply(
            lambda r: _calc_change_pct(r["close"], r["prev_close"])
            if pd.notna(r["prev_close"]) else 0.0,
            axis=1,
        )

        # 涨停/跌停判定
        df["is_limit_up"] = df.apply(
            lambda r: r["change_pct"] >= LIMIT_UP_THRESHOLD and _is_main_board(r["code"]),
            axis=1,
        )
        df["is_limit_down"] = df.apply(
            lambda r: r["change_pct"] <= LIMIT_DOWN_THRESHOLD and _is_main_board(r["code"]),
            axis=1,
        )

        today_str = latest_date
        yesterday = _get_prev_trading_day(df, today_str)
        today_data = df[df["date"] == today_str].copy()

        # 股票名称映射
        stock_name_map = {}
        stocks_df = pd.read_sql_query("SELECT code, name FROM stocks", conn)
        stock_name_map = dict(zip(stocks_df["code"], stocks_df["name"]))

        # ── 1. 涨停/跌停家数 ──
        limit_up_today = today_data[today_data["is_limit_up"]]
        limit_down_today = today_data[today_data["is_limit_down"]]
        limit_up_count = len(limit_up_today)
        limit_down_count = len(limit_down_today)

        # ── 2. 昨日涨停今日表现 ──
        yesterday_limit_up_today_perf = _calc_yesterday_lu_perf(df, today_str, yesterday)

        # ── 3. 炸板率 ──
        broken_count, broken_rate, limit_up_with_broken = _calc_broken_rate(limit_up_today)

        # ── 4. 连板统计 ──
        consecutive_boards = _compute_consecutive_boards(df, today_str, stock_name_map)

        # ── 5. 连板股今日表现追踪 ──
        consecutive_tracking = _track_consecutive_today(df, today_str, yesterday, stock_name_map)

        # ── 6. 晋级率 ──
        promotion_rates = _compute_promotion_rates(df, today_str, yesterday)

        # ── 7. 板块热力榜 ──
        sector_heat = _compute_sector_heat(limit_up_with_broken, today_data, stock_name_map)

        # ── 8. 炸板复盘排行 ──
        broken_review = _compute_broken_review(df, today_str, yesterday, stock_name_map)

        # ── 9. 综合评分 ──
        composite_score = _compute_composite_score(
            yesterday_limit_up_today_perf,
            broken_rate,
            limit_up_count,
            limit_down_count,
            promotion_rates,
        )

        # ── 10. 龙头对比数据 ──
        leaders = _get_leaders(consecutive_boards, limit_up_with_broken, stock_name_map)

        # ── 11. 涨停股详情 ──
        limit_up_detail = _build_limit_up_detail(
            limit_up_with_broken, today_data, df, stock_name_map
        )

        # ── 12. 炸板池 ──
        broken_detail = _build_broken_detail(
            limit_up_with_broken, today_data, df, stock_name_map
        )

        conn.close()

        result = {
            "date": today_str,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": {
                "yesterdayLimitUpToday": round(yesterday_limit_up_today_perf, 2),
                "brokenRate": round(broken_rate, 1),
                "limitUpCount": limit_up_count,
                "limitDownCount": limit_down_count,
                "promotionRate": promotion_rates.get("default", {
                    "level": "2进3", "rate": 0, "success": 0, "total": 0,
                }),
                "promotionRates": promotion_rates,
                "compositeScore": composite_score,
            },
            "limitUpStocks": limit_up_detail,
            "consecutiveBoards": consecutive_boards,
            "consecutiveTracking": consecutive_tracking,
            "brokenBoards": broken_detail,
            "sectorHeat": sector_heat,
            "brokenReview": broken_review,
            "leaders": leaders,
        }

        # 保存情绪快照到数据库
        try:
            save_emotion_snapshot(today_str, result)
        except Exception:
            pass

        return result

    except Exception as e:
        print(f"[EmotionService] Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return _empty_result(str(e))


def _calc_yesterday_lu_perf(df: pd.DataFrame, today_str: str, yesterday: Optional[str]) -> float:
    """计算昨日涨停股今天的加权平均涨幅。"""
    if not yesterday:
        return 0.0
    yesterday_data = df[df["date"] == yesterday]
    yesterday_limit_up = yesterday_data[yesterday_data["is_limit_up"]]
    yesterday_codes = set(yesterday_limit_up["code"].tolist())

    today_data = df[df["date"] == today_str]
    today_yesterday_lu = today_data[today_data["code"].isin(yesterday_codes)]
    if today_yesterday_lu.empty:
        return 0.0

    total_amount = today_yesterday_lu["amount"].sum()
    if total_amount > 0:
        return (
            (today_yesterday_lu["change_pct"] * today_yesterday_lu["amount"]).sum()
            / total_amount
        )
    return today_yesterday_lu["change_pct"].mean()


def _calc_broken_rate(limit_up_today: pd.DataFrame):
    """计算炸板率。返回 (炸板数, 炸板率, 带炸板标记的涨停股 DataFrame)。"""
    if limit_up_today.empty:
        return 0, 0.0, limit_up_today

    lu = limit_up_today.copy()
    lu["prev_close"] = lu["prev_close"].fillna(lu["close"])
    lu["limit_price"] = (lu["prev_close"] * 1.10).round(2)
    lu["is_broken"] = (
        (lu["high"] >= lu["limit_price"] * 0.998) &
        (lu["close"] < lu["limit_price"] * 0.995)
    )
    broken_count = int(lu["is_broken"].sum())
    broken_rate = (broken_count / max(len(lu), 1)) * 100
    return broken_count, broken_rate, lu


def _compute_consecutive_boards(df: pd.DataFrame, today_str: str, stock_name_map: dict) -> list[dict]:
    """计算连板梯队。"""
    boards = []
    today_data = df[df["date"] == today_str]
    today_lu = today_data[today_data["is_limit_up"]]

    for _, row in today_lu.iterrows():
        code = row["code"]
        stock_hist = df[df["code"] == code].sort_values("date", ascending=False)
        consecutive = 0
        for _, hist_row in stock_hist.iterrows():
            if hist_row["is_limit_up"]:
                consecutive += 1
            else:
                break

        if consecutive >= 1:
            boards.append({
                "code": code,
                "name": stock_name_map.get(code, ""),
                "boardCount": consecutive,
                "sealAmount": round(row.get("amount", 0), 0),
                "sealRatio": 0,
                "changePct": round(row["change_pct"], 2),
                "turnover": 0,
                "status": "封死",
                "tag": _guess_tag(consecutive, row),
                "isHighest": False,
                "todayChangePct": round(row["change_pct"], 2),
                "todayOpenPct": round(((row["open"] - row["prev_close"]) / max(row["prev_close"], 1)) * 100, 2),
            })

    if boards:
        max_board = max(b["boardCount"] for b in boards)
        highest = [b for b in boards if b["boardCount"] == max_board]
        highest.sort(key=lambda x: x["sealAmount"], reverse=True)
        highest[0]["isHighest"] = True

    boards.sort(key=lambda x: (-x["boardCount"], -x["sealAmount"]))
    return boards


def _track_consecutive_today(df: pd.DataFrame, today_str: str, yesterday: Optional[str], stock_name_map: dict) -> list[dict]:
    """连板股今日表现追踪（昨日涨停 → 今日表现）。"""
    if not yesterday:
        return []

    yesterday_data = df[df["date"] == yesterday]
    yesterday_lu = yesterday_data[yesterday_data["is_limit_up"]]
    yesterday_codes = set(yesterday_lu["code"].tolist())

    today_data = df[df["date"] == today_str]
    today = today_data[today_data["code"].isin(yesterday_codes)].copy()

    tracking = []
    for _, row in today.iterrows():
        code = row["code"]
        yesterday_row = yesterday_data[yesterday_data["code"] == code]
        if yesterday_row.empty:
            continue

        prev_close = yesterday_row.iloc[0]["close"]
        open_pct = ((row["open"] - prev_close) / max(prev_close, 1)) * 100
        close_pct = row["change_pct"]
        high_pct = ((row["high"] - prev_close) / max(prev_close, 1)) * 100
        low_pct = ((row["low"] - prev_close) / max(prev_close, 1)) * 100

        # 状态判定
        if row["is_limit_up"]:
            status = "✓ 封死"
            status_color = "green"
        elif high_pct > 5:
            status = "⚠ 回落"
            status_color = "yellow"
        elif close_pct < -3:
            status = "✗ 走弱"
            status_color = "red"
        else:
            status = "○ 震荡"
            status_color = "gray"

        # 昨日连板数
        stock_hist = df[(df["code"] == code) & (df["date"] <= yesterday)]
        consecutive = 0
        for _, h in stock_hist.sort_values("date", ascending=False).iterrows():
            if h["is_limit_up"]:
                consecutive += 1
            else:
                break

        tracking.append({
            "code": code,
            "name": stock_name_map.get(code, ""),
            "boardCount": consecutive,
            "openPct": round(open_pct, 2),
            "highPct": round(high_pct, 2),
            "closePct": round(close_pct, 2),
            "lowPct": round(low_pct, 2),
            "status": status,
            "statusColor": status_color,
            "amount": round(row.get("amount", 0), 0),
        })

    tracking.sort(key=lambda x: -x["closePct"])
    return tracking


def _compute_sector_heat(limit_up_stocks: pd.DataFrame, today_data: pd.DataFrame, stock_name_map: dict) -> list[dict]:
    """板块热力榜——按板块聚合涨停数据。"""
    from collections import defaultdict

    sector_stats = defaultdict(lambda: {
        "count": 0, "max_board": 0, "total_amount": 0.0,
        "stocks": [], "broken": 0,
    })

    for _, row in limit_up_stocks.iterrows():
        code = row["code"]
        sector = _get_sector(code)
        if sector == "—":
            continue

        # 计算连板数
        stock_hist = today_data[today_data["code"] == code]
        # (简化：直接用 boardCount 字段)
        board_count = 1

        s = sector_stats[sector]
        s["count"] += 1
        s["total_amount"] += row.get("amount", 0)
        if row.get("is_broken", False):
            s["broken"] += 1
        s["stocks"].append({
            "code": code,
            "name": stock_name_map.get(code, ""),
            "changePct": round(row["change_pct"], 2),
            "boardCount": board_count,
        })

    result = []
    for sector, stats in sector_stats.items():
        stats["stocks"].sort(key=lambda x: -x["changePct"])
        result.append({
            "sector": sector,
            "count": stats["count"],
            "broken": stats["broken"],
            "totalAmount": round(stats["total_amount"], 0),
            "maxBoard": stats["max_board"],
            "stocks": stats["stocks"][:5],  # Top 5
        })

    result.sort(key=lambda x: -x["count"])
    return result


def _compute_broken_review(df: pd.DataFrame, today_str: str, yesterday: Optional[str], stock_name_map: dict) -> list[dict]:
    """炸板复盘排行——昨日涨停但今天表现差的股票。"""
    if not yesterday:
        return []

    yesterday_data = df[df["date"] == yesterday]
    yesterday_lu = yesterday_data[yesterday_data["is_limit_up"]]
    yesterday_codes = set(yesterday_lu["code"].tolist())

    today_data = df[df["date"] == today_str]
    today = today_data[today_data["code"].isin(yesterday_codes)]

    review = []
    for _, row in today.iterrows():
        code = row["code"]
        if row["is_limit_up"]:
            continue  # 涨停的不算炸板

        prev_close = row.get("prev_close", row["close"])
        high_pct = ((row["high"] - prev_close) / max(prev_close, 1)) * 100
        close_pct = row["change_pct"]
        pullback = high_pct - close_pct

        if high_pct > 3:  # 盘中有过一定涨幅
            review.append({
                "code": code,
                "name": stock_name_map.get(code, ""),
                "highPct": round(high_pct, 2),
                "currentPct": round(close_pct, 2),
                "pullback": round(pullback, 2),
                "amount": round(row.get("amount", 0), 0),
                "openPct": round(((row["open"] - prev_close) / max(prev_close, 1)) * 100, 2),
            })

    review.sort(key=lambda x: -x["pullback"])
    return review[:20]


def _compute_promotion_rates(df: pd.DataFrame, today_str: str, yesterday_str: Optional[str]) -> dict:
    """计算各梯队晋级率。"""
    rates = {}
    if not yesterday_str:
        rates["default"] = {"level": "2进3", "rate": 0, "success": 0, "total": 0}
        return rates

    today_data = df[df["date"] == today_str]
    yesterday_data = df[df["date"] == yesterday_str]

    for _, stock_row in yesterday_data.iterrows():
        code = stock_row["code"]
        if not stock_row["is_limit_up"]:
            continue

        stock_hist = df[(df["code"] == code) & (df["date"] < yesterday_str)]
        if stock_hist.empty:
            continue

        consecutive_before = 0
        for _, h in stock_hist.sort_values("date", ascending=False).iterrows():
            if h["is_limit_up"]:
                consecutive_before += 1
            else:
                break

        yesterday_board = consecutive_before + 1
        if yesterday_board < 1 or yesterday_board > 5:
            continue

        today_row = today_data[today_data["code"] == code]
        if today_row.empty:
            continue
        today_lu = today_row.iloc[0]["is_limit_up"]

        level_key = f"{yesterday_board}进{yesterday_board + 1}"
        if level_key not in rates:
            rates[level_key] = {"level": level_key, "success": 0, "total": 0}
        rates[level_key]["total"] += 1
        if today_lu:
            rates[level_key]["success"] += 1

    for key in rates:
        total = rates[key]["total"]
        success = rates[key]["success"]
        rates[key]["rate"] = round((success / max(total, 1)) * 100, 0)

    if "2进3" in rates:
        rates["default"] = rates["2进3"]
    elif rates:
        rates["default"] = list(rates.values())[0]
    else:
        rates["default"] = {"level": "2进3", "rate": 0, "success": 0, "total": 0}

    return rates


def _get_leaders(consecutive_boards: list, limit_up_stocks: pd.DataFrame, stock_name_map: dict) -> list[dict]:
    """龙头股对比——取最高连板的 3 只股票。"""
    if not consecutive_boards:
        return []

    leaders = []
    for board in consecutive_boards[:3]:
        leaders.append({
            "code": board["code"],
            "name": board["name"],
            "boardCount": board["boardCount"],
            "changePct": board["changePct"],
            "sealAmount": board["sealAmount"],
            "turnover": board["turnover"],
            "tag": board["tag"],
            "isHighest": board.get("isHighest", False),
        })
    return leaders


def _compute_composite_score(yester_perf, broken_rate, limit_up_count, limit_down_count, promotion_rates) -> int:
    """综合评分 0-100。"""
    perf_score = min(100, max(0, ((yester_perf + 5) / 10) * 100))
    broken_score = max(0, 100 - (broken_rate / 60) * 100)
    lu_score = min(100, (limit_up_count / 80) * 100)
    promo_score = promotion_rates.get("default", {}).get("rate", 50)

    score = round(perf_score * 0.3 + broken_score * 0.3 + lu_score * 0.2 + promo_score * 0.2)
    return min(100, max(0, score))


def _guess_tag(board_count: int, row: pd.Series) -> str:
    """根据日线数据猜测形态标签。"""
    prev_close = row.get("prev_close", row.get("close", 1))
    limit_price = round(prev_close * 1.10, 2)
    low = row.get("low", 0)
    high = row.get("high", 0)

    if abs(high - low) / max(prev_close, 1) < 0.005:
        return "一字板"
    if low >= limit_price * 0.995:
        return "T字板"
    if board_count == 1:
        return "首板"
    return "换手板"


def _build_limit_up_detail(limit_up_stocks: pd.DataFrame, today_data: pd.DataFrame, all_df: pd.DataFrame, stock_name_map: dict) -> list[dict]:
    """构建涨停股详情列表。"""
    details = []
    for _, row in limit_up_stocks.iterrows():
        code = row["code"]
        amount = row.get("amount", 0)
        stock_hist = all_df[all_df["code"] == code].sort_values("date", ascending=False)
        consecutive = 0
        for _, h in stock_hist.iterrows():
            if h["is_limit_up"]:
                consecutive += 1
            else:
                break

        closes = stock_hist.head(20)["close"].tolist()
        closes.reverse()

        details.append({
            "code": code,
            "name": stock_name_map.get(code, ""),
            "firstLimitTime": "N/A",
            "lastLimitTime": "N/A",
            "sealAmount": round(amount, 0),
            "floatCap": round(amount * 10, 0),
            "sealRatio": 0.05,
            "boardCount": consecutive,
            "tag": _guess_tag(consecutive, row),
            "sector": _get_sector(code),
            "reason": "—",
            "changePct": round(row["change_pct"], 2),
            "turnover": 0,
            "intraData": [round(c, 2) for c in closes],
        })

    details.sort(key=lambda x: x["sealAmount"], reverse=True)
    return details


def _build_broken_detail(limit_up_stocks: pd.DataFrame, today_data: pd.DataFrame, all_df: pd.DataFrame, stock_name_map: dict) -> list[dict]:
    """构建炸板池。"""
    details = []
    for _, row in limit_up_stocks.iterrows():
        if not row.get("is_broken", False):
            continue

        code = row["code"]
        prev_close = row.get("prev_close", row["close"])

        stock_hist = all_df[all_df["code"] == code].sort_values("date", ascending=False)
        consecutive = 0
        for _, h in stock_hist.iterrows():
            if h["is_limit_up"]:
                consecutive += 1
            else:
                break

        details.append({
            "code": code,
            "name": stock_name_map.get(code, ""),
            "highPct": round(row["change_pct"], 2),
            "currentPct": round(row["change_pct"], 2),
            "brokenDuration": 0,
            "brokenAmount": round(row.get("amount", 0), 0),
            "sector": _get_sector(code),
            "boardCount": consecutive,
            "status": "观察",
        })

    details.sort(key=lambda x: x["brokenAmount"], reverse=True)
    return details


def _empty_result(error: str = "") -> dict:
    """返回空结果。"""
    return {
        "date": "",
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error": error if error else "数据库不可用或无数据",
        "metrics": {
            "yesterdayLimitUpToday": 0, "brokenRate": 0,
            "limitUpCount": 0, "limitDownCount": 0,
            "promotionRate": {"level": "2进3", "rate": 0, "success": 0, "total": 0},
            "promotionRates": {}, "compositeScore": 0,
        },
        "limitUpStocks": [], "consecutiveBoards": [],
        "consecutiveTracking": [], "brokenBoards": [],
        "sectorHeat": [], "brokenReview": [], "leaders": [],
    }
