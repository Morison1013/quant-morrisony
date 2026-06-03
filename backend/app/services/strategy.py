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
# 指标 5：双K线影线组合策略（拆分为8个独立策略）
# ────────────────────────────────────────────

def _compute_ma20_slope(ma20_series: pd.Series, window: int = 5) -> float:
    """计算 MA20 的 N 日斜率。"""
    if len(ma20_series) < window + 1:
        return 0.0
    recent = ma20_series.iloc[-(window + 1):]
    if pd.isna(recent.iloc[0]) or pd.isna(recent.iloc[-1]):
        return 0.0
    slope = (recent.iloc[-1] - recent.iloc[0]) / window
    return slope


def determine_trend_with_slope(df: pd.DataFrame) -> str:
    """判断趋势：上涨/下跌/震荡（放宽条件）。"""
    if len(df) < 25:
        return "sideways"
    ma20 = df["close"].rolling(window=20, min_periods=20).mean()
    if pd.isna(ma20.iloc[-1]):
        return "sideways"
    last_close = df.iloc[-1]["close"]
    last_ma20 = ma20.iloc[-1]
    slope = _compute_ma20_slope(ma20, window=5)

    # 放宽条件：只看斜率方向，不强制要求价格在MA20上方/下方
    # 允许价格偏离MA20不超过3%仍判断为趋势
    deviation = abs(last_close - last_ma20) / last_ma20

    if slope > 0:
        # MA20向上，只要价格不偏离太远就判断为上涨
        if last_close >= last_ma20 * 0.97:  # 允许偏离3%
            return "up"
    elif slope < 0:
        # MA20向下，只要价格不偏离太远就判断为下跌
        if last_close <= last_ma20 * 1.03:  # 允许偏离3%
            return "down"

    # 斜率接近0时，看价格位置判断
    if abs(slope) < 0.01:
        if last_close > last_ma20 * 1.02:
            return "up"
        elif last_close < last_ma20 * 0.98:
            return "down"

    return "sideways"


def _calc_shadows(high: float, low: float, close: float, open_: float) -> dict:
    """计算影线长度。"""
    body = abs(close - open_)
    upper_shadow = high - max(close, open_)
    lower_shadow = min(close, open_) - low
    return {"body": body, "upper_shadow": upper_shadow, "lower_shadow": lower_shadow}


def _is_long_lower_shadow(shadows: dict, body_ratio: float = 0.1) -> bool:
    """长下影线判断（使用相对比例）。

    Args:
        body_ratio: 小实体判断阈值（实体占振幅的比例，默认10%）

    判断标准：
    - 小实体（实体占比<10%）：下影明显长于上影（>1.5倍）
    - 正常实体：下影 >= 实体×0.8 且 上影 <= 实体×1.0
    """
    body = shadows["body"]
    lower = shadows["lower_shadow"]
    upper = shadows["upper_shadow"]

    # 使用相对比例判断小实体
    total_range = body + lower + upper
    if total_range > 0:
        body_pct = body / total_range
    else:
        body_pct = 0

    if body_pct < body_ratio or body < 0.5:
        # 小实体/十字星：下影明显长于上影即可
        return lower > upper * 1.5 and lower > 0

    # 正常实体：放宽条件
    return lower >= body * 0.8 and upper <= body * 1.0


def _is_long_upper_shadow(shadows: dict, body_ratio: float = 0.1) -> bool:
    """长上影线判断（使用相对比例）。

    Args:
        body_ratio: 小实体判断阈值（实体占振幅的比例，默认10%）

    判断标准：
    - 小实体（实体占比<10%）：上影明显长于下影（>1.5倍）
    - 正常实体：上影 >= 实体×0.8 且 下影 <= 实体×1.0
    """
    body = shadows["body"]
    lower = shadows["lower_shadow"]
    upper = shadows["upper_shadow"]

    # 使用相对比例判断小实体
    total_range = body + lower + upper
    if total_range > 0:
        body_pct = body / total_range
    else:
        body_pct = 0

    if body_pct < body_ratio or body < 0.5:
        # 小实体/十字星：上影明显长于下影即可
        return upper > lower * 1.5 and upper > 0

    # 正常实体：放宽条件
    return upper >= body * 0.8 and lower <= body * 1.0


def _classify_volume(volume: float, avg_vol_5: float) -> str:
    """量能分类：huge/increase/moderate/stable/decrease"""
    if avg_vol_5 <= 0:
        return "stable"
    ratio = volume / avg_vol_5
    if ratio > 1.5:
        return "huge"
    elif ratio > 1.3:
        return "increase"
    elif ratio >= 1.0:
        return "moderate"
    elif ratio >= 0.7:
        return "stable"
    else:
        return "decrease"


def check_dual_shadow_base(df: pd.DataFrame) -> dict:
    """
    检测双K线影线组合基础信息。

    Returns:
        {
            "trend": "up"/"down"/"sideways",
            "combo_type": "lower_to_upper"/"upper_to_lower"/None,
            "k1_is_yin": bool,
            "k1_vol_type": str,
            "k2_vol_type": str,
            "k1_shadows": dict,
            "k2_shadows": dict,
            "avg_vol_5": float,
        }
    """
    if len(df) < 30:
        return {"trend": "sideways", "combo_type": None}

    # 计算MA20和趋势
    df_temp = df.copy()
    df_temp["ma20"] = df_temp["close"].rolling(window=20, min_periods=20).mean()
    df_temp["avg_vol_5"] = df_temp["volume"].rolling(window=5, min_periods=5).mean().shift(1)

    trend = determine_trend_with_slope(df_temp)
    if trend == "sideways":
        return {"trend": "sideways", "combo_type": None}

    # K1和K2
    k1 = df.iloc[-2]
    k2 = df.iloc[-1]

    # 计算影线
    k1_shadows = _calc_shadows(k1["high"], k1["low"], k1["close"], k1["open"])
    k2_shadows = _calc_shadows(k2["high"], k2["low"], k2["close"], k2["open"])

    k1_has_lower = _is_long_lower_shadow(k1_shadows)
    k1_has_upper = _is_long_upper_shadow(k1_shadows)
    k2_has_lower = _is_long_lower_shadow(k2_shadows)
    k2_has_upper = _is_long_upper_shadow(k2_shadows)

    # 组合类型
    combo_type = None
    if k1_has_lower and k2_has_upper:
        combo_type = "lower_to_upper"
    elif k1_has_upper and k2_has_lower:
        combo_type = "upper_to_lower"

    if combo_type is None:
        return {"trend": trend, "combo_type": None}

    # K1颜色
    k1_is_yin = k1["close"] < k1["open"]

    # 量能
    avg_vol_5 = df_temp.iloc[-2]["avg_vol_5"]
    if pd.isna(avg_vol_5):
        avg_vol_5 = df.iloc[-7:-2]["volume"].mean()

    k1_vol_type = _classify_volume(k1["volume"], avg_vol_5)
    k2_vol_type = _classify_volume(k2["volume"], avg_vol_5)

    return {
        "trend": trend,
        "combo_type": combo_type,
        "k1_is_yin": k1_is_yin,
        "k1_vol_type": k1_vol_type,
        "k2_vol_type": k2_vol_type,
        "k1_shadows": k1_shadows,
        "k2_shadows": k2_shadows,
        "avg_vol_5": avg_vol_5,
        "k1": k1,
        "k2": k2,
    }


# ────────────────────────────────────────────
# 8个独立策略定义
# ────────────────────────────────────────────

def check_continue_down(df: pd.DataFrame) -> dict:
    """
    中继下跌（下跌趋势）
    条件：下影接上影 + K1阴线 + K1放量/平量 + K2缩量
    """
    base = check_dual_shadow_base(df)
    if base["trend"] != "down" or base["combo_type"] != "lower_to_upper":
        return {"signal": False, "name": "中继下跌"}

    if not base["k1_is_yin"]:
        return {"signal": False, "name": "中继下跌"}

    k1_ok = base["k1_vol_type"] in ["increase", "stable", "moderate"]
    k2_ok = base["k2_vol_type"] == "decrease"

    return {
        "signal": k1_ok and k2_ok,
        "name": "中继下跌",
        "strength": -2,
        "type": "bearish",
        "volume_match": k1_ok and k2_ok,
        "details": base,
    }


def check_support_range(df: pd.DataFrame) -> dict:
    """
    支撑位震荡选方向（下跌趋势）
    条件：下影接上影 + K1阳线 + K1放量 + K2缩量
    """
    base = check_dual_shadow_base(df)
    if base["trend"] != "down" or base["combo_type"] != "lower_to_upper":
        return {"signal": False, "name": "支撑位震荡选方向"}

    if base["k1_is_yin"]:
        return {"signal": False, "name": "支撑位震荡选方向"}

    k1_ok = base["k1_vol_type"] == "increase"
    k2_ok = base["k2_vol_type"] == "decrease"

    return {
        "signal": k1_ok and k2_ok,
        "name": "支撑位震荡选方向",
        "strength": -1,
        "type": "neutral",
        "volume_match": k1_ok and k2_ok,
        "details": base,
    }


def check_support_rebound(df: pd.DataFrame) -> dict:
    """
    支撑位资金抢反弹（下跌趋势）
    条件：上影接下影 + K1阳线 + K1放量 + K2放量
    """
    base = check_dual_shadow_base(df)
    if base["trend"] != "down" or base["combo_type"] != "upper_to_lower":
        return {"signal": False, "name": "支撑位资金抢反弹"}

    if base["k1_is_yin"]:
        return {"signal": False, "name": "支撑位资金抢反弹"}

    k1_ok = base["k1_vol_type"] == "increase"
    k2_ok = base["k2_vol_type"] in ["increase", "huge"]

    return {
        "signal": k1_ok and k2_ok,
        "name": "支撑位资金抢反弹",
        "strength": 1,
        "type": "bullish",
        "volume_match": k1_ok and k2_ok,
        "details": base,
    }


def check_short_stop(df: pd.DataFrame) -> dict:
    """
    短期止跌（下跌趋势）
    条件：上影接下影 + K1阴线 + K1平/放量 + K2缩量
    """
    base = check_dual_shadow_base(df)
    if base["trend"] != "down" or base["combo_type"] != "upper_to_lower":
        return {"signal": False, "name": "短期止跌"}

    if not base["k1_is_yin"]:
        return {"signal": False, "name": "短期止跌"}

    k1_ok = base["k1_vol_type"] in ["increase", "stable", "moderate"]
    k2_ok = base["k2_vol_type"] == "decrease"

    return {
        "signal": k1_ok and k2_ok,
        "name": "短期止跌",
        "strength": 2,
        "type": "bullish",
        "volume_match": k1_ok and k2_ok,
        "details": base,
    }


def check_diverge_start(df: pd.DataFrame) -> dict:
    """
    开始有分歧（上涨趋势）
    条件：下影接上影 + K1阴线 + K1放量 + K2放量
    """
    base = check_dual_shadow_base(df)
    if base["trend"] != "up" or base["combo_type"] != "lower_to_upper":
        return {"signal": False, "name": "开始有分歧"}

    if not base["k1_is_yin"]:
        return {"signal": False, "name": "开始有分歧"}

    k1_ok = base["k1_vol_type"] == "increase"
    k2_ok = base["k2_vol_type"] == "increase"

    return {
        "signal": k1_ok and k2_ok,
        "name": "开始有分歧",
        "strength": -1,
        "type": "bearish",
        "volume_match": k1_ok and k2_ok,
        "details": base,
    }


def check_diverge_strong(df: pd.DataFrame) -> dict:
    """
    分歧但强势看新高（上涨趋势）
    条件：下影接上影 + K1阳线 + K1温和放量(1.0-1.5) + K2缩量
    """
    base = check_dual_shadow_base(df)
    if base["trend"] != "up" or base["combo_type"] != "lower_to_upper":
        return {"signal": False, "name": "分歧但强势看新高"}

    if base["k1_is_yin"]:
        return {"signal": False, "name": "分歧但强势看新高"}

    k1_ok = base["k1_vol_type"] == "moderate"  # 温和放量 1.0-1.5
    k2_ok = base["k2_vol_type"] == "decrease"

    return {
        "signal": k1_ok and k2_ok,
        "name": "分歧但强势看新高",
        "strength": 1,
        "type": "bullish",
        "volume_match": k1_ok and k2_ok,
        "details": base,
    }


def check_strong_support(df: pd.DataFrame) -> dict:
    """
    承接力度大只承接不追高（上涨趋势）
    条件：上影接下影 + K1阳线 + K1巨量(>1.5倍) + K2放量
    """
    base = check_dual_shadow_base(df)
    if base["trend"] != "up" or base["combo_type"] != "upper_to_lower":
        return {"signal": False, "name": "承接力度大只承接不追高"}

    if base["k1_is_yin"]:
        return {"signal": False, "name": "承接力度大只承接不追高"}

    k1_ok = base["k1_vol_type"] == "huge"  # 巨量 > 1.5倍
    k2_ok = base["k2_vol_type"] in ["increase", "huge"]

    return {
        "signal": k1_ok and k2_ok,
        "name": "承接力度大只承接不追高",
        "strength": 0,
        "type": "neutral",
        "volume_match": k1_ok and k2_ok,
        "details": base,
    }


def check_weak_support(df: pd.DataFrame) -> dict:
    """
    承接低可能出现短期顶（上涨趋势）
    条件：上影接下影 + K1阴线 + K1放量 + K2缩量
    """
    base = check_dual_shadow_base(df)
    if base["trend"] != "up" or base["combo_type"] != "upper_to_lower":
        return {"signal": False, "name": "承接低可能出现短期顶"}

    if not base["k1_is_yin"]:
        return {"signal": False, "name": "承接低可能出现短期顶"}

    k1_ok = base["k1_vol_type"] == "increase"
    k2_ok = base["k2_vol_type"] == "decrease"

    return {
        "signal": k1_ok and k2_ok,
        "name": "承接低可能出现短期顶",
        "strength": -2,
        "type": "bearish",
        "volume_match": k1_ok and k2_ok,
        "details": base,
    }


# ────────────────────────────────────────────
# 指标 6：通达信策略1（复合信号策略 - 合并版）
# ────────────────────────────────────────────

def check_tdx_strategy1(df: pd.DataFrame) -> dict:
    """
    通达信策略1 - 复合信号检测（合并版）。

    包含多个信号的综合检测：
    - 游资进场、抄底、精准买点、短买点、奔牛、黑马、波段买点、波段卖点、大黑马

    Returns:
        {
            "signal": bool,  # 是否触发任一信号
            "name": "通达信策略1",
            "signals": list,  # 触发的具体信号列表
            "buy_line": float,
            "sell_line": float,
            "is_bullish": bool,
        }
    """
    if len(df) < 150:
        return {"signal": False, "name": "通达信策略1", "signals": []}

    closes = df["close"]
    volumes = df["volume"]
    highs = df["high"]
    lows = df["low"]
    opens = df["open"]

    # ZIG作为买线，其3日均线作为卖线
    zig_line = calc_zig(closes, 10.0)
    buy_line = zig_line
    sell_line = buy_line.rolling(3).mean()
    is_bullish = buy_line.iloc[-1] >= sell_line.iloc[-1]

    signals = []

    # 检测各个子信号（复用之前的逻辑）
    result = check_tdx_strategy1_full(df)
    if result["has_signal"]:
        signals = result["signals"]

    return {
        "signal": len(signals) > 0,
        "name": "通达信策略1",
        "signals": signals,
        "buy_line": round(buy_line.iloc[-1], 2),
        "sell_line": round(sell_line.iloc[-1], 2),
        "is_bullish": is_bullish,
        "strength": sum(s.get("strength", 0) for s in signals),
    }


def check_tdx_strategy1_full(df: pd.DataFrame) -> dict:
    """通达信策略1完整检测逻辑。"""
    if len(df) < 150:
        return {"has_signal": False, "signals": []}

    closes = df["close"]
    volumes = df["volume"]
    highs = df["high"]
    lows = df["low"]
    opens = df["open"]

    # ZIG(3,10)作为买线，其3日均线作为卖线
    zig_line = calc_zig(closes, 10.0)
    buy_line = zig_line
    sell_line = buy_line.rolling(3).mean()
    is_bullish = buy_line.iloc[-1] >= sell_line.iloc[-1]

    # 基线：REF(LLV(C,30),1)的2日均线
    llv30 = calc_llv(closes, 30)
    baseline = llv30.shift(1).rolling(2).mean()

    # 量能饱和度
    vol_ma5 = volumes.rolling(5).mean()
    vol_ma60 = volumes.rolling(60).mean()
    volume_saturation = (vol_ma5.iloc[-1] / vol_ma60.iloc[-1] * 100) if vol_ma60.iloc[-1] > 0 else 0

    signals = []

    # 1. 游资进场信号
    try:
        varf1 = (highs - lows) / closes * 100
        vol_increase = volumes.iloc[-1] > volumes.iloc[-2]
        price_increase = closes.iloc[-1] > closes.iloc[-2]

        recent_30 = df.tail(30)
        signal_count = 0
        for i in range(len(recent_30) - 1):
            if recent_30.iloc[i+1]["volume"] > recent_30.iloc[i]["volume"] and \
               recent_30.iloc[i+1]["close"] > recent_30.iloc[i]["close"]:
                signal_count += 1

        if vol_increase and price_increase and is_bullish and signal_count <= 1:
            signals.append({"name": "游资进场", "type": "bullish", "strength": 3, "color": "#ADD8E6"})
    except Exception:
        pass

    # 2. 抄底信号
    try:
        vars1 = (closes - calc_llv(closes, 9)) / (calc_hhv(closes, 9) - calc_llv(closes, 9)) * 100
        vars3 = vars1.rolling(3).mean()
        vars4 = vars1.ewm(span=3).mean()
        cross_up = vars3.iloc[-1] > vars4.iloc[-1] and vars3.iloc[-2] <= vars4.iloc[-2]
        under_20 = vars3.iloc[-1] < 20

        if cross_up and under_20 and is_bullish:
            signals.append({"name": "抄底", "type": "bullish", "strength": 2, "color": "#FF00FF"})
    except Exception:
        pass

    # 3. 精准买点
    try:
        x1 = calc_hhv(highs, 5) - calc_llv(lows, 5)
        x2 = (closes - calc_llv(lows, 5)) / x1 * 100
        x3 = x2.rolling(5).mean()
        cross_up = x2.iloc[-1] > x3.iloc[-1] and x2.iloc[-2] <= x3.iloc[-2]

        if cross_up and is_bullish:
            signals.append({"name": "精准买点", "type": "bullish", "strength": 2, "color": "#FFFF00"})
    except Exception:
        pass

    # 4. 短买点
    try:
        momentum = closes.pct_change() * 100
        cross_11 = momentum.iloc[-1] > 11 and momentum.iloc[-2] <= 11
        k1_yin = closes.iloc[-2] < opens.iloc[-2]
        k2_yang = closes.iloc[-1] > opens.iloc[-1]
        reversal = k1_yin and k2_yang and closes.iloc[-1] > opens.iloc[-2]
        avg_vol = volumes.rolling(20).mean().iloc[-1]
        turnover_ratio = volumes.iloc[-1] / avg_vol if avg_vol > 0 else 0

        if cross_11 and reversal and turnover_ratio > 3 and is_bullish:
            signals.append({"name": "短买点", "type": "bullish", "strength": 1, "color": "#FF00FF"})
    except Exception:
        pass

    # 5. 奔牛信号
    try:
        sma_signal = closes.rolling(13).mean()
        ema_signal = closes.ewm(span=8).mean()
        cross_up = sma_signal.iloc[-1] > ema_signal.iloc[-1] and sma_signal.iloc[-2] <= ema_signal.iloc[-2]

        if cross_up and is_bullish:
            signals.append({"name": "奔牛", "type": "bullish", "strength": 2, "color": "#00AAFF"})
    except Exception:
        pass

    # 6. 黑马信号
    try:
        ema3 = closes.ewm(span=3).mean()
        ema21 = closes.ewm(span=21).mean()
        golden_cross = ema3.iloc[-1] > ema21.iloc[-1] and ema3.iloc[-2] <= ema21.iloc[-2]

        last_death = 0
        for i in range(len(df) - 2, max(0, len(df) - 50), -1):
            if ema3.iloc[i] < ema21.iloc[i] and ema3.iloc[i-1] >= ema21.iloc[i-1]:
                last_death = len(df) - i
                break

        vol_ok = 0.8 < volume_saturation / 100 < 1.5

        if golden_cross and vol_ok and last_death > 15 and is_bullish:
            signals.append({"name": "黑马", "type": "bullish", "strength": 3, "color": "#FF6600"})
    except Exception:
        pass

    # 7. 波段买点
    try:
        cross_up = buy_line.iloc[-1] > sell_line.iloc[-1] and buy_line.iloc[-2] <= sell_line.iloc[-2]
        if cross_up and is_bullish:
            signals.append({"name": "波段买点", "type": "bullish", "strength": 2, "color": "#FFB6C1"})
    except Exception:
        pass

    # 8. 波段卖点
    try:
        zig5 = calc_zig(closes, 5.0)
        down_3 = zig5.iloc[-1] < zig5.iloc[-2] and zig5.iloc[-2] < zig5.iloc[-3] and zig5.iloc[-3] < zig5.iloc[-4]
        if down_3 and not is_bullish:
            signals.append({"name": "波段卖点", "type": "bearish", "strength": -2, "color": "#FFFFFF"})
    except Exception:
        pass

    # 9. 大黑马信号
    try:
        comp_sma = (closes - calc_llv(lows, 55)) / (calc_hhv(highs, 55) - calc_llv(lows, 55)) * 100
        comp_sma = comp_sma - 50
        cross_zero = comp_sma.iloc[-1] > 0 and comp_sma.iloc[-2] <= 0
        ema_cond = closes.ewm(span=13).mean().iloc[-1] < closes.iloc[-1] * 1.4

        if cross_zero and ema_cond and is_bullish:
            signals.append({"name": "大黑马", "type": "bullish", "strength": 4, "color": "#0000FF"})
    except Exception:
        pass

    return {
        "has_signal": len(signals) > 0,
        "signals": signals,
        "buy_line": round(buy_line.iloc[-1], 2),
        "sell_line": round(sell_line.iloc[-1], 2),
        "is_bullish": is_bullish,
        "baseline": round(baseline.iloc[-1], 2) if not pd.isna(baseline.iloc[-1]) else None,
        "volume_saturation": round(volume_saturation, 1),
    }


# ────────────────────────────────────────────
# 指标 7：通达信策略2（主图量化策略）
# ────────────────────────────────────────────

def check_tdx_strategy2(df: pd.DataFrame) -> dict:
    """
    通达信策略2 - 主图量化策略。

    核心要素：
    1. MA5(#F00FF0)、MA10、MA20均线
    2. 买线=ZIG(3,10)，卖线=MA(买线,3)
    3. K线颜色填充：空头绿色渐变、多头蓝色渐变
    4. 基线、量能饱和度、换手率
    5. 多个信号：游资进场、抄底、精准买、短买点、奔牛、黑马、波段买卖、大黑马
    6. ZIG图标标记

    Returns:
        {
            "signal": bool,
            "name": "通达信策略2",
            "signals": list,
            "ma_values": dict,
            "buy_line": float,
            "sell_line": float,
            "is_bullish": bool,
            "kline_color": str,  # 当前K线应填充颜色
            "zig_icons": list,  # ZIG图标标记
        }
    """
    if len(df) < 60:
        return {"signal": False, "name": "通达信策略2", "signals": []}

    closes = df["close"]
    volumes = df["volume"]
    highs = df["high"]
    lows = df["low"]
    opens = df["open"]

    # 1. 均线系统
    ma5 = closes.rolling(5).mean()
    ma10 = closes.rolling(10).mean()
    ma20 = closes.rolling(20).mean()

    # 2. 买线=ZIG(3,10)，卖线=MA(买线,3)
    # ZIG(3,10)表示用收盘价，阈值10%
    zig_line = calc_zig(closes, 10.0)
    buy_line = zig_line
    sell_line = buy_line.rolling(3).mean()

    # 3. K线颜色判断
    is_bullish = buy_line.iloc[-1] >= sell_line.iloc[-1]
    kline_color = "blue_gradient" if is_bullish else "green_gradient"

    # 检测买线上穿卖线（特殊颜色）
    cross_up = buy_line.iloc[-1] > sell_line.iloc[-1] and buy_line.iloc[-2] <= sell_line.iloc[-2]
    if cross_up:
        kline_color = "#00AAFF"

    # 4. 基线与量能饱和度
    llv30 = calc_llv(closes, 30)
    baseline = llv30.shift(1).rolling(2).mean()

    vol_ma5 = volumes.rolling(5).mean()
    vol_ma60 = volumes.rolling(60).mean()
    volume_saturation = (vol_ma5.iloc[-1] / vol_ma60.iloc[-1] * 100) if vol_ma60.iloc[-1] > 0 else 0

    # 换手率估算
    avg_vol = volumes.rolling(20).mean().iloc[-1]
    turnover = (volumes.iloc[-1] / avg_vol) if avg_vol > 0 else 0

    signals = []

    # 5. 游资进场信号
    try:
        # VARF1 = (H-L)/C*100 振幅
        varf1 = (highs - lows) / closes * 100
        # VAR101 = VARF1的2日均线
        var101 = varf1.rolling(2).mean()
        # VAR111条件：VARF1 < 前VAR101 且 量增价涨
        var111_cond = varf1.iloc[-1] < var101.iloc[-2] and \
                      volumes.iloc[-1] > volumes.iloc[-2] and \
                      closes.iloc[-1] > closes.iloc[-2]

        # 30周期内唯一检测
        recent_30 = df.tail(30)
        unique_check = True
        for i in range(len(recent_30) - 2):
            if recent_30.iloc[i+1]["volume"] > recent_30.iloc[i]["volume"] and \
               recent_30.iloc[i+1]["close"] > recent_30.iloc[i]["close"] and \
               i != len(recent_30) - 2:
                unique_check = False
                break

        if var111_cond and unique_check and is_bullish:
            signals.append({
                "name": "游资进场",
                "type": "bullish",
                "strength": 3,
                "color": "#ADD8E6",  # lightblue
                "position": "baseline_0.97",
                "text": "游资进场",
            })
    except Exception:
        pass

    # 6. 抄底信号
    try:
        # VARS1 = (C-LLV(C,9))/(HHV(C,9)-LLV(C,9))*100
        vars1 = (closes - calc_llv(closes, 9)) / (calc_hhv(closes, 9) - calc_llv(closes, 9)) * 100
        # VARS3 = SMA(VARS1,3,1)
        vars3 = vars1.ewm(span=3).mean()  # 简化EMA代替SMA
        # VARS4 = SMA(VARS3,3,1)
        vars4 = vars3.ewm(span=3).mean()

        cross_up = vars3.iloc[-1] > vars4.iloc[-1] and vars3.iloc[-2] <= vars4.iloc[-2]
        under_20 = vars3.iloc[-1] < 20

        if cross_up and under_20 and is_bullish:
            signals.append({
                "name": "抄底",
                "type": "bullish",
                "strength": 2,
                "color": "#FF00FF",  # magenta
                "position": "baseline_0.94",
                "text": "抄底",
            })
    except Exception:
        pass

    # 7. 精准买点
    try:
        # X1 = HHV(H,5) - LLV(L,5)
        x1 = calc_hhv(highs, 5) - calc_llv(lows, 5)
        # X2 = (C-LLV(L,5))/X1*100
        x2 = (closes - calc_llv(lows, 5)) / x1 * 100
        # X3 = SMA(X2,5,1)
        x3 = x2.ewm(span=5).mean()

        cross_up = x2.iloc[-1] > x3.iloc[-1] and x2.iloc[-2] <= x3.iloc[-2]

        if cross_up and is_bullish:
            signals.append({
                "name": "精准买",
                "type": "bullish",
                "strength": 2,
                "color": "#FFFF00",  # 黄色
                "position": "low_0.99",
                "text": "精准买",
            })
    except Exception:
        pass

    # 8. 短买点
    try:
        # 动量线
        momentum = closes.diff() / closes.shift(1) * 100
        momentum_ma = momentum.rolling(11).mean()
        cross_11 = momentum.iloc[-1] > momentum_ma.iloc[-1]

        # S1/S2反转结构
        s1 = closes.iloc[-2] < opens.iloc[-2]  # 前一日阴线
        s2 = closes.iloc[-1] > opens.iloc[-1]  # 当日阳线
        reversal = s1 and s2 and closes.iloc[-1] > opens.iloc[-2]

        if cross_11 and reversal and turnover >= 3 and is_bullish:
            signals.append({
                "name": "短买点",
                "type": "bullish",
                "strength": 1,
                "color": "#FF00FF",  # magenta
                "position": "baseline_0.94",
                "text": "短买点",
            })
    except Exception:
        pass

    # 9. 奔牛信号
    try:
        # 特定平滑值
        sma_val = closes.rolling(8).mean()
        ema_val = closes.ewm(span=13).mean()
        cross = sma_val.iloc[-1] > ema_val.iloc[-1] and sma_val.iloc[-2] <= ema_val.iloc[-2]

        if cross and is_bullish:
            signals.append({
                "name": "奔牛",
                "type": "bullish",
                "strength": 2,
                "color": "#00AAFF",
                "position": "baseline_0.98",
                "text": "奔牛",
            })
    except Exception:
        pass

    # 10. 黑马信号
    try:
        ema3 = closes.ewm(span=3).mean()
        ema21 = closes.ewm(span=21).mean()
        golden = ema3.iloc[-1] > ema21.iloc[-1] and ema3.iloc[-2] <= ema21.iloc[-2]

        # 量能适中（80%-150%）
        vol_ok = 80 < volume_saturation < 150

        # 距上次死叉>15周期
        last_death_dist = 0
        for i in range(len(df) - 2, max(0, len(df) - 50), -1):
            if ema3.iloc[i] < ema21.iloc[i]:
                last_death_dist = len(df) - i
                break

        if golden and vol_ok and last_death_dist > 15 and is_bullish:
            signals.append({
                "name": "黑马",
                "type": "bullish",
                "strength": 3,
                "color": "#FF6600",
                "position": "baseline_0.98",
                "text": "黑马",
            })
    except Exception:
        pass

    # 11. 波段买卖
    try:
        # 波段买点：买线上穿卖线
        wave_buy = buy_line.iloc[-1] > sell_line.iloc[-1] and buy_line.iloc[-2] <= sell_line.iloc[-2]
        if wave_buy and is_bullish:
            signals.append({
                "name": "波段买点",
                "type": "bullish",
                "strength": 2,
                "color": "#FFB6C1",  # lightred
                "position": "baseline_0.98",
                "text": "--进场",
            })

        # 波段卖点：ZIG(3,5)连续三期下降
        zig5 = calc_zig(closes, 5.0)
        wave_sell = zig5.iloc[-1] < zig5.iloc[-2] and zig5.iloc[-2] < zig5.iloc[-3] and zig5.iloc[-3] < zig5.iloc[-4]
        if wave_sell and not is_bullish:
            signals.append({
                "name": "波段卖点",
                "type": "bearish",
                "strength": -2,
                "color": "#FFFFFF",
                "position": "high_1.05",
                "text": "落袋为安",
            })
    except Exception:
        pass

    # 12. 大黑马信号
    try:
        # 复合SMA
        comp_sma = (closes - calc_llv(lows, 55)) / (calc_hhv(highs, 55) - calc_llv(lows, 55)) * 100
        comp_sma = comp_sma - 50
        cross_zero = comp_sma.iloc[-1] > 0 and comp_sma.iloc[-2] <= 0

        # 另一EMA条件<40
        ema13 = closes.ewm(span=13).mean()
        ema_cond = ema13.iloc[-1] < closes.iloc[-1] * 1.4  # 简化条件

        if cross_zero and ema_cond and is_bullish:
            signals.append({
                "name": "大黑马",
                "type": "bullish",
                "strength": 4,
                "color": "#0000FF",
                "position": "baseline_0.94",
                "text": "-大黑马",
            })
    except Exception:
        pass

    # 13. ZIG图标标记
    zig_icons = []
    try:
        # ZIG(3,10)上穿前值
        zig10 = calc_zig(closes, 10.0)
        zig_up = zig10.iloc[-1] > zig10.iloc[-2] and zig10.iloc[-2] <= zig10.iloc[-3]
        zig_down = zig10.iloc[-1] < zig10.iloc[-2] and zig10.iloc[-2] >= zig10.iloc[-3]

        if zig_up:
            zig_icons.append({
                "icon": "icon7",
                "position": "low_0.97",
                "color": "green",
            })
        if zig_down:
            zig_icons.append({
                "icon": "icon8",
                "position": "high_1.04",
                "color": "red",
            })

        # ZIG(3,8)上穿前值 -> 绝佳标记
        zig8 = calc_zig(closes, 8.0)
        zig8_up = zig8.iloc[-1] > zig8.iloc[-2] and zig8.iloc[-2] <= zig8.iloc[-3]
        if zig8_up:
            zig_icons.append({
                "icon": "star",
                "text": "★绝佳",
                "position": "low_0.928",
                "color": "red",
            })
    except Exception:
        pass

    return {
        "signal": len(signals) > 0,
        "name": "通达信策略2",
        "signals": signals,
        "ma_values": {
            "ma5": round(ma5.iloc[-1], 2) if not pd.isna(ma5.iloc[-1]) else None,
            "ma10": round(ma10.iloc[-1], 2) if not pd.isna(ma10.iloc[-1]) else None,
            "ma20": round(ma20.iloc[-1], 2) if not pd.isna(ma20.iloc[-1]) else None,
        },
        "buy_line": round(buy_line.iloc[-1], 2),
        "sell_line": round(sell_line.iloc[-1], 2),
        "is_bullish": is_bullish,
        "kline_color": kline_color,
        "baseline": round(baseline.iloc[-1], 2) if not pd.isna(baseline.iloc[-1]) else None,
        "volume_saturation": round(volume_saturation, 1),
        "turnover": round(turnover, 2),
        "zig_icons": zig_icons,
        "strength": sum(s.get("strength", 0) for s in signals),
    }


# ────────────────────────────────────────────
# 双K线影线策略字典（用于综合检测）
# ────────────────────────────────────────────
DUAL_SHADOW_STRATEGIES = {
    "continue_down": {"func": check_continue_down, "name": "中继下跌", "group": "下跌趋势"},
    "support_range": {"func": check_support_range, "name": "支撑位震荡选方向", "group": "下跌趋势"},
    "support_rebound": {"func": check_support_rebound, "name": "支撑位资金抢反弹", "group": "下跌趋势"},
    "short_stop": {"func": check_short_stop, "name": "短期止跌", "group": "下跌趋势"},
    "diverge_start": {"func": check_diverge_start, "name": "开始有分歧", "group": "上涨趋势"},
    "diverge_strong": {"func": check_diverge_strong, "name": "分歧但强势看新高", "group": "上涨趋势"},
    "strong_support": {"func": check_strong_support, "name": "承接力度大只承接不追高", "group": "上涨趋势"},
    "weak_support": {"func": check_weak_support, "name": "承接低可能出现短期顶", "group": "上涨趋势"},
}


def check_trend_shadow_strategy(df: pd.DataFrame) -> dict:
    """
    综合检测所有双K线影线策略。
    返回匹配的第一个信号（按优先级：bullish > neutral > bearish）。
    """
    results = []
    for key, info in DUAL_SHADOW_STRATEGIES.items():
        result = info["func"](df)
        if result["signal"]:
            results.append({
                "strategy_key": key,
                "strategy_name": result["name"],
                "signal_type": result["type"],
                "strength": result["strength"],
                "volume_match": result["volume_match"],
            })

    if not results:
        return {
            "has_signal": False,
            "signals": [],
            "is_strong_signal": False,
            "trend": "unknown",
            "signal_strength": 0,
        }

    # 按 strength 排序（优先 bullish）
    results.sort(key=lambda x: -x["strength"])

    # 提取趋势信息
    primary = results[0]
    trend = "上涨" if primary["signal_type"] == "bullish" else "下跌" if primary["signal_type"] == "bearish" else "震荡"

    return {
        "has_signal": True,
        "is_strong_signal": primary["volume_match"],
        "signals": results,
        "primary_signal": primary,
        "trend": trend,
        "signal_strength": primary["strength"],
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

    # 趋势影线组合策略
    trend_shadow = check_trend_shadow_strategy(df)

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
    if trend_shadow["is_strong_signal"]:
        # 根据信号强度调整加分
        score += 20 + trend_shadow.get("signal_strength", 0) * 5

    return {
        "stock_code": df.attrs.get("symbol", ""),
        "latest_date": str(df.iloc[-1]["date"].date()),
        "latest_close": round(df.iloc[-1]["close"], 2),
        "trend": trend_shadow["trend"],
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
        "trend_shadow_strategy": trend_shadow,
        "strategy_score": score,
        "signal_summary": _build_signal_summary(ma_bullish, monthly_golden, weekly_death, daily_death, arb, rubbing, trend_shadow),
    }


def _build_signal_summary(
    ma_bullish: bool,
    monthly_golden: bool,
    weekly_death: bool,
    daily_death: bool,
    arb: dict,
    rubbing: dict | None = None,
    trend_shadow: dict | None = None,
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

    # 趋势影线组合策略信号
    if trend_shadow:
        ts = trend_shadow
        if ts["has_signal"]:
            if ts["is_strong_signal"]:
                signals.append(f"📊 趋势影线组合【{ts['signal_name']}】（{ts['action']}）")
            else:
                signals.append(f"📊 趋势影线组合【{ts['signal_name']}】量能未匹配（{ts['volume_info'].get('pattern', 'unknown')}）")
        else:
            trend_desc = {"up": "上涨", "down": "下跌", "sideways": "震荡"}
            signals.append(f"ℹ️ {trend_desc.get(ts['trend'], '未知')}趋势，影线组合形态不满足")

    return signals
