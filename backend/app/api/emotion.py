"""
打板情绪监控 API 路由。
"""

from fastapi import APIRouter, Query

router = APIRouter(prefix="/emotion", tags=["emotion"])


@router.get("/snapshot")
def get_emotion_snapshot():
    """获取最新情绪快照。"""
    from app.services.emotion import compute_emotion_data
    return compute_emotion_data()


@router.get("/refresh")
def refresh_emotion_data():
    """手动触发情绪数据重新计算。"""
    from app.services.emotion import compute_emotion_data
    return compute_emotion_data()


@router.get("/history")
def get_emotion_history(days: int = Query(default=30, ge=1, le=90)):
    """获取情绪快照历史（用于情绪周期日历）。"""
    from app.services.db import load_emotion_history
    history = load_emotion_history(days)
    return {"data": history}


@router.get("/leaders")
def get_leader_comparison(codes: str = Query(default="", description="逗号分隔的股票代码")):
    """龙头股对比。"""
    from app.services.db import get_conn
    import pandas as pd

    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return {"error": "请指定股票代码"}

    conn = get_conn()
    if conn is None:
        return {"error": "数据库不可用"}

    # 获取最近数据
    today_data = pd.read_sql_query(
        """
        SELECT code, date, open, high, low, close, volume, amount
        FROM daily_kline
        WHERE date = (SELECT MAX(date) FROM daily_kline)
        AND code IN ({})
        """.format(",".join("?" * len(code_list))),
        conn,
        params=code_list,
    )

    # 获取前一日收盘价
    prev_data = pd.read_sql_query(
        """
        SELECT code, date, close
        FROM daily_kline
        WHERE date < (SELECT MAX(date) FROM daily_kline)
        AND code IN ({})
        ORDER BY date DESC
        """.format(",".join("?" * len(code_list))),
        conn,
        params=code_list,
    )
    conn.close()

    prev_map = {}
    if not prev_data.empty:
        for _, row in prev_data.groupby("code").first().iterrows():
            prev_map[row.name] = row["close"]

    result = []
    for _, row in today_data.iterrows():
        code = row["code"]
        prev_close = prev_map.get(code, row["close"])
        result.append({
            "code": code,
            "date": str(row["date"]),
            "open": round(row["open"], 2),
            "high": round(row["high"], 2),
            "low": round(row["low"], 2),
            "close": round(row["close"], 2),
            "openPct": round(((row["open"] - prev_close) / max(prev_close, 1)) * 100, 2),
            "highPct": round(((row["high"] - prev_close) / max(prev_close, 1)) * 100, 2),
            "closePct": round(((row["close"] - prev_close) / max(prev_close, 1)) * 100, 2),
            "volume": round(row["volume"], 0),
            "amount": round(row["amount"], 0),
        })

    return {"data": result}
