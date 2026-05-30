"""
策略指标计算模块。

所有计算函数均为纯 Pandas 向量化操作，输入 DataFrame → 输出增强 DataFrame。
"""

import pandas as pd
import numpy as np


# ────────────────────────────────────────────
# 指标 1：均线系统 (60/55/30/20/10/5 日均线多头排列)
# ────────────────────────────────────────────
MA_PERIODS = [5, 10, 20, 30, 55, 60]


def compute_ma(df: pd.DataFrame) -> pd.DataFrame:
    """计算多周期均线，返回增强 DataFrame。"""
    out = df.copy()
    for period in MA_PERIODS:
        out[f"ma{period}"] = out["close"].rolling(window=period, min_periods=period).mean()
    return out


def check_ma_bullish_alignment(df: pd.DataFrame) -> bool:
    """
    检查最新一天的均线是否多头排列（从上到下：MA5 > MA10 > MA20 > MA30 > MA55 > MA60）。
    """
    if f"ma{MA_PERIODS[-1]}" not in df.columns or df.iloc[-1][f"ma{MA_PERIODS[-1]}"] is np.nan:
        return False
    last = df.iloc[-1]
    for i in range(len(MA_PERIODS) - 1):
        short = f"ma{MA_PERIODS[i]}"
        long_ = f"ma{MA_PERIODS[i + 1]}"
        if pd.isna(last.get(short)) or pd.isna(last.get(long_)):
            return False
        if last[short] <= last[long_]:
            return False
    return True


def get_ma_alignment_status(df: pd.DataFrame) -> list[dict]:
    """返回每根 K 线的均线状态。"""
    results = []
    for idx, row in df.iterrows():
        if pd.isna(row.get("ma5")):
            continue
        is_bullish = True
        for i in range(len(MA_PERIODS) - 1):
            s = f"ma{MA_PERIODS[i]}"
            l = f"ma{MA_PERIODS[i + 1]}"
            if pd.isna(row[s]) or pd.isna(row[l]) or row[s] <= row[l]:
                is_bullish = False
                break
        results.append({
            "date": str(row["date"].date()),
            "is_bullish": is_bullish,
            **{f"ma{p}": round(row[f"ma{p}"], 2) for p in MA_PERIODS if not pd.isna(row[f"ma{p}"])},
        })
    return results


# ────────────────────────────────────────────
# 指标 2：MACD（月金叉，周/日未死叉）
# ────────────────────────────────────────────
def compute_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """
    计算日级别 MACD。
    返回包含 DIF, DEA, MACD_HIST 的增强 DataFrame。
    """
    out = df.copy()
    ema_fast = out["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = out["close"].ewm(span=slow, adjust=False).mean()
    out["dif"] = ema_fast - ema_slow
    out["dea"] = out["dif"].ewm(span=signal, adjust=False).mean()
    out["macd_hist"] = 2 * (out["dif"] - out["dea"])  # 同花顺风格
    return out


def compute_weekly_macd(df: pd.DataFrame) -> tuple[float | None, float | None]:
    """
    基于日线数据重采样到周线，计算最新周 MACD。
    返回 (dif, dea)。
    """
    weekly = df.set_index("date").resample("W-FRI").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()
    if len(weekly) < 26:
        return None, None
    ema_fast = weekly["close"].ewm(span=12, adjust=False).mean()
    ema_slow = weekly["close"].ewm(span=26, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=9, adjust=False).mean()
    return round(dif.iloc[-1], 4), round(dea.iloc[-1], 4)


def compute_monthly_macd(df: pd.DataFrame) -> tuple[float | None, float | None]:
    """
    基于日线数据重采样到月线，计算最新月 MACD。
    返回 (dif, dea)。
    """
    monthly = df.set_index("date").resample("ME").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()
    if len(monthly) < 26:
        return None, None
    ema_fast = monthly["close"].ewm(span=12, adjust=False).mean()
    ema_slow = monthly["close"].ewm(span=26, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=9, adjust=False).mean()
    return round(dif.iloc[-1], 4), round(dea.iloc[-1], 4)


def check_macd_golden_cross(dif: float | None, dea: float | None) -> bool:
    """判断是否金叉 (DIF > DEA 且前一日 DIF <= DEA) 或持续金叉状态。"""
    if dif is None or dea is None:
        return False
    return dif > dea


def check_macd_death_cross(dif: float | None, dea: float | None) -> bool:
    """判断是否死叉 (DIF < DEA)。"""
    if dif is None or dea is None:
        return False
    return dif < dea


# ────────────────────────────────────────────
# 指标 3：成交量逐日递减 + 低于近一月均量 → 可隔日套利
# ────────────────────────────────────────────
def check_volume_decrease(df: pd.DataFrame, lookback_days: int = 3) -> bool:
    """
    检查近 N 日成交量是否逐日递减。
    """
    if len(df) < lookback_days:
        return False
    recent = df.tail(lookback_days)["volume"].values
    for i in range(len(recent) - 1):
        if recent[i] <= recent[i + 1]:  # 不递减
            return False
    return True


def check_volume_below_monthly_avg(df: pd.DataFrame) -> bool:
    """
    检查最新日成交量是否低于近 20 交易日均量。
    """
    if len(df) < 21:
        return False
    avg_vol = df.tail(21).head(20)["volume"].mean()
    latest_vol = df.iloc[-1]["volume"]
    return bool(latest_vol < avg_vol)


def check_arbitrage_signal(df: pd.DataFrame) -> dict:
    """
    综合判断是否触发"可隔日套利"信号。

    Returns:
        包含信号详情的 dict。
    """
    vol_decreasing = check_volume_decrease(df)
    vol_below_avg = check_volume_below_monthly_avg(df)
    is_arbitrage = vol_decreasing and vol_below_avg

    recent_3 = df.tail(3)[["date", "volume"]].to_dict("records")
    for r in recent_3:
        r["date"] = str(r["date"].date())

    return {
        "is_arbitrage_signal": is_arbitrage,
        "volume_decreasing_3d": vol_decreasing,
        "volume_below_monthly_avg": vol_below_avg,
        "recent_volumes": recent_3,
        "monthly_avg_volume": round(df.tail(21).head(20)["volume"].mean(), 0) if len(df) >= 21 else None,
    }


# ────────────────────────────────────────────
# 指标 4：红色揉搓线（BOLL 中轨附近 + 近期新高 + 缩量 + K 线形态）
# ────────────────────────────────────────────
def compute_boll(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """计算 BOLL 指标（中轨、上轨、下轨）。"""
    out = df.copy()
    out["boll_mid"] = out["close"].rolling(window=period, min_periods=period).mean()
    rolling_std = out["close"].rolling(window=period, min_periods=period).std()
    out["boll_upper"] = out["boll_mid"] + std_dev * rolling_std
    out["boll_lower"] = out["boll_mid"] - std_dev * rolling_std
    return out


def check_near_boll_mid(close: float, boll_mid: float, threshold: float = 0.01) -> bool:
    """收盘价是否在 BOLL 中轨附近（偏差 ≤ threshold）。"""
    if pd.isna(boll_mid) or boll_mid == 0:
        return False
    return abs(close - boll_mid) / boll_mid <= threshold


def check_recent_new_high(df: pd.DataFrame, high_window: int = 20, check_window: int = 5) -> bool:
    """
    前 check_window 天内是否有某天创了 high_window 日新高。
    """
    if len(df) < high_window + 1:
        return False
    for i in range(1, min(check_window + 1, len(df))):
        row = df.iloc[-i]
        high_val = row["high"]
        # 计算当天的 20 日最高（包含当天往前 20 天）
        start_idx = max(0, len(df) - i - high_window)
        end_idx = len(df) - i
        recent_20_high = df.iloc[start_idx:end_idx]["high"].max()
        if high_val >= recent_20_high:
            return True
    return False


def check_volume_shrink(df: pd.DataFrame, threshold: float = 0.6, vol_window: int = 20) -> bool:
    """
    最新日成交量是否 ≤ 近 vol_window 日均量 × threshold。
    """
    if len(df) < vol_window + 1:
        return False
    avg_vol = df.iloc[-(vol_window + 1):-1]["volume"].mean()
    latest_vol = df.iloc[-1]["volume"]
    return bool(latest_vol <= avg_vol * threshold)


def _upper_shadow(high: float, close: float, open_: float) -> float:
    return high - max(close, open_)


def _lower_shadow(low: float, close: float, open_: float) -> float:
    return min(close, open_) - low


def _body(close: float, open_: float) -> float:
    return abs(close - open_)


def check_red_rubbing_line(df: pd.DataFrame) -> dict:
    """
    检测揉搓线形态（洗盘版）。

    揉搓线本质 = 多空拉锯的洗盘信号：
    - 近 3 根 K 线中，至少 1 根有长上影，至少 1 根有长下影
    - 整体为阳线或十字星（非明显阴线）

    长影线定义：影线 ≥ 实体 × 1.2 且 ≥ 全天范围 25%
    """
    default = {
        "is_rubbing_line": False,
        "k1_is_red": False,
        "k2_is_red": False,
        "k1_is_long_upper": False,
        "k2_is_long_lower": False,
        "k1_upper_ratio": None,
        "k2_lower_ratio": None,
    }
    if len(df) < 2:
        return default

    # 看最近 3 根（不足则用 2 根）
    lookback = min(3, len(df))
    candles = [df.iloc[-(i + 1)] for i in range(lookback)][::-1]  # 从旧到新

    has_long_upper = False
    has_long_lower = False
    all_non_bearish = True

    for c in candles:
        up = _upper_shadow(c["high"], c["close"], c["open"])
        low = _lower_shadow(c["low"], c["close"], c["open"])
        body = _body(c["close"], c["open"])
        rng = c["high"] - c["low"]

        # 长影线
        if rng > 0 and up >= body * 1.2 and up >= rng * 0.25:
            has_long_upper = True
        if rng > 0 and low >= body * 1.2 and low >= rng * 0.25:
            has_long_lower = True

        # 非明显阴线：收盘 >= 开盘，或小实体十字星
        is_bearish = c["close"] < c["open"] and (rng == 0 or body / rng > 0.3)
        if is_bearish:
            all_non_bearish = False

    # 最后一根单独记录（用于 UI 展示）
    k1 = df.iloc[-2]
    k2 = df.iloc[-1]
    k1_up = _upper_shadow(k1["high"], k1["close"], k1["open"])
    k1_body = _body(k1["close"], k1["open"])
    k1_range = k1["high"] - k1["low"]
    k2_low = _lower_shadow(k2["low"], k2["close"], k2["open"])
    k2_body = _body(k2["close"], k2["open"])
    k2_range = k2["high"] - k2["low"]

    k1_red = bool(k1["close"] >= k1["open"] or (k1_range > 0 and k1_body / k1_range < 0.2))
    k2_red = bool(k2["close"] >= k2["open"] or (k2_range > 0 and k2_body / k2_range < 0.2))
    k1_long_upper = bool(k1_range > 0 and k1_up >= k1_body * 1.2 and k1_up >= k1_range * 0.25)
    k2_long_lower = bool(k2_range > 0 and k2_low >= k2_body * 1.2 and k2_low >= k2_range * 0.25)

    return {
        "is_rubbing_line": bool(has_long_upper and has_long_lower and all_non_bearish),
        "k1_is_red": k1_red,
        "k2_is_red": k2_red,
        "k1_is_long_upper": k1_long_upper,
        "k2_is_long_lower": k2_long_lower,
        "k1_upper_ratio": round(k1_up / k1_body, 2) if k1_body > 0 else None,
        "k2_lower_ratio": round(k2_low / k2_body, 2) if k2_body > 0 else None,
    }


def check_rubbing_strategy(df: pd.DataFrame) -> dict:
    """
    完整揉搓线策略（洗盘版）：
    1. 收盘价在 BOLL 中轨附近（偏差 ≤ 3%）
    2. 近 10 日内有创 20 日新高（放宽到 10 天）
    3. 缩量（当日量 ≤ 20 日均量 × 0.85）
    4. 揉搓线形态（近 3 日有长上影 + 长下影）
    """
    if len(df) < 25:
        return {
            "buy_signal": False,
            "is_near_boll_mid": False,
            "had_new_high": False,
            "is_shrink_vol": False,
            "rubbing_line": check_red_rubbing_line(df),
        }

    boll_mid = df.iloc[-1].get("boll_mid")
    near_mid = check_near_boll_mid(df.iloc[-1]["close"], boll_mid, threshold=0.03)
    new_high = check_recent_new_high(df, high_window=20, check_window=10)
    shrink = check_volume_shrink(df, threshold=0.85)
    rubbing = check_red_rubbing_line(df)

    buy_signal = bool(near_mid and new_high and shrink and rubbing["is_rubbing_line"])

    return {
        "buy_signal": buy_signal,
        "is_near_boll_mid": near_mid,
        "had_new_high": new_high,
        "is_shrink_vol": shrink,
        "rubbing_line": rubbing,
    }


# ────────────────────────────────────────────
# 主策略管道：组装所有指标
# ────────────────────────────────────────────
def run_strategy_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    运行完整策略管道，返回增强后的 DataFrame。
    """
    df = compute_ma(df)
    df = compute_macd(df)
    df = compute_boll(df)
    return df


def generate_summary(df: pd.DataFrame) -> dict:
    """
    生成策略复盘摘要。
    """
    df = run_strategy_pipeline(df)

    # 均线状态
    ma_bullish = check_ma_bullish_alignment(df)
    ma_statuses = get_ma_alignment_status(df)

    # MACD 状态
    monthly_dif, monthly_dea = compute_monthly_macd(df)
    weekly_dif, weekly_dea = compute_weekly_macd(df)

    monthly_golden = check_macd_golden_cross(monthly_dif, monthly_dea)
    weekly_death = check_macd_death_cross(weekly_dif, weekly_dea)
    daily_death = check_macd_death_cross(df.iloc[-1].get("dif"), df.iloc[-1].get("dea"))

    # 成交量信号
    arb = check_arbitrage_signal(df)

    # 红色揉搓线策略
    rubbing = check_rubbing_strategy(df)

    # 综合打分（简单规则）
    score = 0
    if ma_bullish:
        score += 30
    if monthly_golden and not weekly_death and not daily_death:
        score += 25
    if arb["is_arbitrage_signal"]:
        score += 20
    if rubbing["buy_signal"]:
        score += 25

    return {
        "stock_code": df.attrs.get("symbol", ""),
        "latest_date": str(df.iloc[-1]["date"].date()),
        "latest_close": round(df.iloc[-1]["close"], 2),
        "ma_bullish_alignment": bool(ma_bullish),
        "ma_statuses": ma_statuses[-20:],  # 最近 20 条
        "macd": {
            "monthly": {"dif": monthly_dif, "dea": monthly_dea, "golden_cross": bool(monthly_golden)},
            "weekly": {"dif": weekly_dif, "dea": weekly_dea, "death_cross": bool(weekly_death)},
            "daily": {
                "dif": round(df.iloc[-1]["dif"], 4),
                "dea": round(df.iloc[-1]["dea"], 4),
                "hist": round(df.iloc[-1]["macd_hist"], 4),
                "death_cross": bool(daily_death),
            },
        },
        "volume_signal": arb,
        "boll": {
            "upper": round(df.iloc[-1].get("boll_upper"), 2) if not pd.isna(df.iloc[-1].get("boll_upper")) else None,
            "mid": round(df.iloc[-1].get("boll_mid"), 2) if not pd.isna(df.iloc[-1].get("boll_mid")) else None,
            "lower": round(df.iloc[-1].get("boll_lower"), 2) if not pd.isna(df.iloc[-1].get("boll_lower")) else None,
            "close_near_mid_pct": round(abs(df.iloc[-1]["close"] - df.iloc[-1]["boll_mid"]) / df.iloc[-1]["boll_mid"] * 100, 3) if not pd.isna(df.iloc[-1].get("boll_mid")) and df.iloc[-1]["boll_mid"] != 0 else None,
        },
        "rubbing_strategy": rubbing,
        "strategy_score": score,
        "signal_summary": _build_signal_summary(ma_bullish, monthly_golden, weekly_death, daily_death, arb, rubbing),
    }


def _build_signal_summary(
    ma_bullish: bool,
    monthly_golden: bool,
    weekly_death: bool,
    daily_death: bool,
    arb: dict,
    rubbing: dict | None = None,
) -> list[str]:
    """生成可读信号摘要列表。"""
    signals = []
    if ma_bullish:
        signals.append("✅ 均线多头排列（60/55/30/20/10/5 全向上）")
    else:
        signals.append("❌ 均线未完全多头排列")
    if monthly_golden:
        signals.append("✅ 月线 MACD 金叉")
    else:
        signals.append("❌ 月线 MACD 未金叉")
    if weekly_death:
        signals.append("⚠️ 周线 MACD 死叉")
    else:
        signals.append("✅ 周线 MACD 未死叉")
    if daily_death:
        signals.append("⚠️ 日线 MACD 死叉")
    else:
        signals.append("✅ 日线 MACD 未死叉")
    if arb["is_arbitrage_signal"]:
        signals.append("🎯 触发隔日套利信号（量缩价稳）")
    else:
        signals.append("ℹ️ 未触发隔日套利信号")

    # 红色揉搓线策略信号
    if rubbing:
        rl = rubbing.get("rubbing_line", {})
        if rubbing["buy_signal"]:
            signals.append("🔥 红色揉搓线 BUY 信号！")
        else:
            details = []
            if not rubbing["is_near_boll_mid"]:
                details.append("BOLL偏离")
            if not rubbing["had_new_high"]:
                details.append("未新高")
            if not rubbing["is_shrink_vol"]:
                details.append("未缩量")
            if not rl.get("is_rubbing_line"):
                parts = []
                if not rl.get("k1_is_red") or not rl.get("k2_is_red"):
                    parts.append("非双阳")
                if not rl.get("k1_is_long_upper"):
                    parts.append("K-1无上影")
                if not rl.get("k2_is_long_lower"):
                    parts.append("K-2无下影")
                details.append("形态不符(" + ",".join(parts) + ")")
            signals.append("❌ 揉搓线未触发（" + " / ".join(details) + "）")

    return signals
