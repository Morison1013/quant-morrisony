"""
SQLite 本地数据库管理。

存储全市场 OHLCV 日线数据，扫描和查询直接读本地，速度提升 20×+。
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional

import pandas as pd

DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DB_DIR / "market.db"


def get_conn() -> sqlite3.Connection:
    """获取数据库连接（自动创建目录和数据库）。"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")  # 并发写入优化
    conn.execute("PRAGMA synchronous=NORMAL")  # 性能优化
    conn.execute("PRAGMA cache_size=10000")  # 10MB 缓存
    return conn


def init_db():
    """初始化数据库表结构。"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            code TEXT PRIMARY KEY,
            name TEXT,
            market INTEGER,  -- 0=深圳, 1=上海
            updated_at TEXT  -- 最后更新时间
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_kline (
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            amount REAL,
            PRIMARY KEY (code, date)
        )
    """)

    # 索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kline_code ON daily_kline(code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kline_date ON daily_kline(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kline_code_date ON daily_kline(code, date)")

    # 刷新记录
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refresh_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            finished_at TEXT,
            total_stocks INTEGER,
            success_count INTEGER,
            failed_count INTEGER,
            elapsed_seconds REAL
        )
    """)

    conn.commit()
    conn.close()


def save_stock_list(stocks: list[dict]):
    """保存股票列表到数据库。"""
    conn = get_conn()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn.executemany(
        "INSERT OR REPLACE INTO stocks (code, name, market, updated_at) VALUES (?, ?, ?, ?)",
        [(s["code"], s.get("name", ""), s.get("market", 1), now) for s in stocks],
    )
    conn.commit()
    conn.close()


def save_kline(code: str, df: pd.DataFrame):
    """
    保存单只股票的 K 线数据。

    Args:
        code: 股票代码
        df: 包含 date, open, high, low, close, volume, amount 的 DataFrame
    """
    conn = get_conn()
    rows = []
    for _, row in df.iterrows():
        rows.append((
            code,
            str(row["date"]).split(" ")[0] if " " in str(row["date"]) else str(row["date"]),
            float(row["open"]),
            float(row["high"]),
            float(row["low"]),
            float(row["close"]),
            float(row["volume"]),
            float(row.get("amount", 0)),
        ))

    conn.executemany(
        "INSERT OR REPLACE INTO daily_kline (code, date, open, high, low, close, volume, amount) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def load_kline(code: str, limit: int = 100) -> Optional[pd.DataFrame]:
    """
    从数据库加载单只股票的 K 线数据。

    Args:
        code: 股票代码
        limit: 返回最近 N 条

    Returns:
        DataFrame 或 None（无数据）
    """
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT code, date, open, high, low, close, volume, amount
        FROM daily_kline
        WHERE code = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        conn,
        params=(code, limit),
    )
    conn.close()

    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df.rename(columns={"vol": "volume"})
    return df


def load_stock_list() -> list[dict]:
    """从数据库加载股票列表。"""
    conn = get_conn()
    df = pd.read_sql_query("SELECT code, name, market FROM stocks", conn)
    conn.close()
    if df.empty:
        return []
    return df.to_dict("records")


def get_last_refresh() -> Optional[str]:
    """获取最后一次刷新时间。"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT finished_at FROM refresh_log ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def log_refresh(started: str, finished: str, total: int, success: int, failed: int, elapsed: float):
    """记录刷新日志。"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO refresh_log (started_at, finished_at, total_stocks, success_count, failed_count, elapsed_seconds) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (started, finished, total, success, failed, elapsed),
    )
    conn.commit()
    conn.close()


def get_db_stats() -> dict:
    """获取数据库统计信息。"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stocks")
    stock_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM daily_kline")
    kline_count = cursor.fetchone()[0]
    cursor.execute("SELECT MIN(date), MAX(date) FROM daily_kline")
    date_range = cursor.fetchone()
    conn.close()

    return {
        "stock_count": stock_count,
        "kline_count": kline_count,
        "date_from": date_range[0] if date_range else None,
        "date_to": date_range[1] if date_range else None,
    }
