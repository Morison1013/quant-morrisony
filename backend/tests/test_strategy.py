"""
策略计算模块单元测试。

使用合成的模拟 DataFrame 验证指标计算逻辑，
不依赖 AkShare 网络请求。
"""

import pandas as pd
import numpy as np
import pytest

from app.services.strategy import (
    compute_ma,
    check_ma_bullish_alignment,
    compute_macd,
    compute_weekly_macd,
    compute_monthly_macd,
    compute_boll,
    check_near_boll_mid,
    check_recent_new_high,
    check_volume_shrink,
    check_red_rubbing_line,
    check_rubbing_strategy,
    check_macd_golden_cross,
    check_macd_death_cross,
    check_volume_decrease,
    check_volume_below_monthly_avg,
    check_arbitrage_signal,
    run_strategy_pipeline,
    generate_summary,
)


def _make_fake_df(
    days: int = 100,
    close_start: float = 100.0,
    bullish: bool = True,
) -> pd.DataFrame:
    """
    生成合成的 OHLCV 测试数据。

    Args:
        days: 交易日数量
        close_start: 起始收盘价
        bullish: 若为 True，生成上升趋势（均线多头）
    """
    np.random.seed(42)
    if bullish:
        # 稳定上升趋势
        trend = np.linspace(close_start, close_start * 1.3, days)
        noise = np.random.normal(0, close_start * 0.005, days)
    else:
        # 震荡下跌趋势
        trend = np.linspace(close_start, close_start * 0.8, days)
        noise = np.random.normal(0, close_start * 0.01, days)

    close = trend + noise
    high = close + np.abs(np.random.normal(0, close_start * 0.01, days))
    low = close - np.abs(np.random.normal(0, close_start * 0.01, days))
    open_ = close + np.random.normal(0, close_start * 0.005, days)
    volume = np.random.randint(1000, 5000, days).astype(float)

    dates = pd.date_range(end="2026-05-30", periods=days, freq="B")

    return pd.DataFrame({
        "date": dates,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


class TestMA:
    """均线系统测试。"""

    def test_compute_ma_adds_all_columns(self):
        df = _make_fake_df(100)
        result = compute_ma(df)
        for p in [5, 10, 20, 30, 55, 60]:
            assert f"ma{p}" in result.columns

    def test_ma_values_are_reasonable(self):
        df = _make_fake_df(100, close_start=100.0)
        result = compute_ma(df)
        # MA5 应接近最新收盘价
        latest_ma5 = result.iloc[-1]["ma5"]
        latest_close = result.iloc[-1]["close"]
        assert abs(latest_ma5 - latest_close) / latest_close < 0.05

    def test_ma_bullish_alignment_on_uptrend(self):
        df = _make_fake_df(120, bullish=True)
        df = compute_ma(df)
        # 上升趋势末端大概率多头排列
        result = check_ma_bullish_alignment(df)
        assert result is True

    def test_ma_not_bullish_on_downtrend(self):
        df = _make_fake_df(120, bullish=False)
        df = compute_ma(df)
        result = check_ma_bullish_alignment(df)
        assert result is False

    def test_ma_nan_when_insufficient_data(self):
        df = _make_fake_df(10)  # 不足以计算 MA60
        df = compute_ma(df)
        assert pd.isna(df.iloc[0]["ma60"])


class TestMACD:
    """MACD 指标测试。"""

    def test_compute_macd_adds_columns(self):
        df = _make_fake_df(100)
        result = compute_macd(df)
        assert "dif" in result.columns
        assert "dea" in result.columns
        assert "macd_hist" in result.columns

    def test_macd_golden_cross(self):
        assert check_macd_golden_cross(1.0, 0.5) is True
        assert check_macd_golden_cross(-0.5, -1.0) is True

    def test_macd_no_golden_cross(self):
        assert check_macd_golden_cross(0.5, 1.0) is False

    def test_macd_death_cross(self):
        assert check_macd_death_cross(-1.0, -0.5) is True
        assert check_macd_death_cross(0.5, 1.0) is True

    def test_macd_no_death_cross(self):
        assert check_macd_death_cross(1.0, 0.5) is False

    def test_macd_none_values(self):
        assert check_macd_golden_cross(None, 0.5) is False
        assert check_macd_death_cross(0.5, None) is False

    def test_weekly_macd_returns_tuple(self):
        df = _make_fake_df(200)
        df = compute_macd(df)
        dif, dea = compute_weekly_macd(df)
        assert dif is not None
        assert dea is not None

    def test_monthly_macd_returns_tuple(self):
        # 需要 ~26 个月的数据，按每月 ~22 个交易日 ≈ 572 天，取 700 天保险
        df = _make_fake_df(700)
        df = compute_macd(df)
        dif, dea = compute_monthly_macd(df)
        assert dif is not None
        assert dea is not None

    def test_weekly_macd_insufficient_data(self):
        df = _make_fake_df(20)
        dif, dea = compute_weekly_macd(df)
        assert dif is None
        assert dea is None


class TestVolume:
    """成交量信号测试。"""

    def test_volume_decreasing_true(self):
        df = pd.DataFrame({
            "date": pd.date_range("2026-05-01", periods=5, freq="B"),
            "volume": [5000.0, 4000.0, 3000.0, 2000.0, 1000.0],
        })
        assert check_volume_decrease(df, lookback_days=3) is True

    def test_volume_decreasing_false(self):
        df = pd.DataFrame({
            "date": pd.date_range("2026-05-01", periods=5, freq="B"),
            "volume": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
        })
        assert check_volume_decrease(df, lookback_days=3) is False

    def test_volume_below_monthly_avg_true(self):
        # 前 20 天均量 3000，最后一天 1000
        vols = [3000.0] * 20 + [1000.0]
        df = pd.DataFrame({
            "date": pd.date_range("2026-04-01", periods=21, freq="B"),
            "volume": vols,
        })
        assert check_volume_below_monthly_avg(df) is True

    def test_volume_below_monthly_avg_false(self):
        vols = [3000.0] * 20 + [5000.0]
        df = pd.DataFrame({
            "date": pd.date_range("2026-04-01", periods=21, freq="B"),
            "volume": vols,
        })
        assert check_volume_below_monthly_avg(df) is False

    def test_arbitrage_signal_full(self):
        # 构造满足套利条件的数据
        vols = [3000.0] * 20 + [1500.0, 1200.0, 900.0]  # 最后3天递减且低于均值
        df = pd.DataFrame({
            "date": pd.date_range("2026-04-01", periods=23, freq="B"),
            "volume": vols,
        })
        result = check_arbitrage_signal(df)
        assert result["is_arbitrage_signal"] is True
        assert result["volume_decreasing_3d"] is True
        assert result["volume_below_monthly_avg"] is True

    def test_arbitrage_signal_not_triggered(self):
        vols = [3000.0] * 23
        df = pd.DataFrame({
            "date": pd.date_range("2026-04-01", periods=23, freq="B"),
            "volume": vols,
        })
        result = check_arbitrage_signal(df)
        assert result["is_arbitrage_signal"] is False


class TestPipeline:
    """完整策略管道测试。"""

    def test_run_pipeline_adds_all_columns(self):
        df = _make_fake_df(120)
        result = run_strategy_pipeline(df)
        for p in [5, 10, 20, 30, 55, 60]:
            assert f"ma{p}" in result.columns
        assert "dif" in result.columns
        assert "dea" in result.columns
        assert "macd_hist" in result.columns

    def test_generate_summary_has_all_keys(self):
        df = _make_fake_df(700)
        df.attrs["symbol"] = "000001"
        summary = generate_summary(df)
        assert "stock_code" in summary
        assert "latest_date" in summary
        assert "latest_close" in summary
        assert "ma_bullish_alignment" in summary
        assert "macd" in summary
        assert "volume_signal" in summary
        assert "strategy_score" in summary
        assert "signal_summary" in summary
        assert isinstance(summary["strategy_score"], int)
        assert 0 <= summary["strategy_score"] <= 100

    def test_generate_summary_signal_count(self):
        df = _make_fake_df(700)
        summary = generate_summary(df)
        # 固定 6 条信号摘要（均线/MACD月/周/日/套利/揉搓线）
        assert len(summary["signal_summary"]) == 6


class TestBOLL:
    """BOLL 指标测试。"""

    def test_compute_boll_adds_columns(self):
        df = _make_fake_df(100)
        result = compute_boll(df)
        assert "boll_mid" in result.columns
        assert "boll_upper" in result.columns
        assert "boll_lower" in result.columns

    def test_boll_upper_above_lower(self):
        df = _make_fake_df(100)
        result = compute_boll(df)
        # 上轨应始终大于下轨
        last = result.iloc[-1]
        assert last["boll_upper"] > last["boll_lower"]

    def test_check_near_boll_mid(self):
        assert check_near_boll_mid(100.0, 100.5, 0.01) is True
        assert check_near_boll_mid(100.0, 102.0, 0.01) is False

    def test_check_near_boll_mid_nan(self):
        assert check_near_boll_mid(100.0, float("nan"), 0.01) is False
        assert check_near_boll_mid(100.0, 0, 0.01) is False


class TestRedRubbingLine:
    """红色揉搓线策略测试。"""

    def _make_rubbing_df(self) -> pd.DataFrame:
        """构造满足揉搓线形态的精确数据。"""
        # K-2 (倒数第2根): 阳线 + 长上影
        # K-1 (最后一根): 阳线 + 长下影
        # 其他条件: BOLL中轨附近 + 近期新高 + 缩量
        base_close = 100.0
        rows = []
        dates = pd.date_range(end="2026-05-30", periods=50, freq="B")

        for i in range(48):
            rows.append({
                "date": dates[i],
                "open": base_close + i * 0.1,
                "close": base_close + i * 0.1 + 0.05,
                "high": base_close + i * 0.1 + 0.15,
                "low": base_close + i * 0.1 - 0.1,
                "volume": 3000.0,
            })

        # K-2: 阳线 + 长上影 (上影>实体 and 上影>下影)
        # open=99, close=100 (body=1), high=105 (upper=5), low=98.5 (lower=1.5)
        rows.append({
            "date": dates[48],
            "open": 99.0,
            "close": 100.0,  # body=1, upper=5, lower=1 → upper>body and upper>lower ✓
            "high": 105.0,
            "low": 98.5,
            "volume": 3000.0,
        })

        # K-1: 阳线 + 长下影 (下影>实体 and 下影>上影)
        # open=99.5, close=100.5 (body=1), high=101 (upper=0.5), low=95 (lower=4.5)
        rows.append({
            "date": dates[49],
            "open": 99.5,
            "close": 100.5,  # body=1, upper=0.5, lower=4.5 → lower>body and lower>upper ✓
            "high": 101.0,
            "low": 95.0,
            "volume": 1000.0,  # 缩量
        })

        return pd.DataFrame(rows)

    def test_red_rubbing_line_detection(self):
        df = self._make_rubbing_df()
        df = compute_boll(df)
        result = check_red_rubbing_line(df)
        assert result["is_rubbing_line"] is True
        assert result["k1_is_red"] is True
        assert result["k2_is_red"] is True
        assert result["k1_is_long_upper"] is True
        assert result["k2_is_long_lower"] is True

    def test_not_rubbing_if_not_both_red(self):
        df = self._make_rubbing_df()
        # 把 K-2 改成明显大阴线（实体占全天范围 70%，不视为十字星）
        df.iloc[-1, df.columns.get_loc("open")] = 105.0
        df.iloc[-1, df.columns.get_loc("close")] = 98.0
        df.iloc[-1, df.columns.get_loc("high")] = 106.0
        df.iloc[-1, df.columns.get_loc("low")] = 95.0
        result = check_red_rubbing_line(df)
        assert result["is_rubbing_line"] is False
        assert result["k2_is_red"] is False

    def test_full_rubbing_strategy(self):
        df = self._make_rubbing_df()
        df = compute_boll(df)
        result = check_rubbing_strategy(df)
        # 收盘价在BOLL中轨附近 + 双阳揉搓 + 缩量 → 应满足
        assert result["is_shrink_vol"] is True
        assert result["rubbing_line"]["is_rubbing_line"] is True

    def test_rubbing_insufficient_data(self):
        df = pd.DataFrame({
            "date": pd.date_range("2026-05-01", periods=2, freq="B"),
            "open": [100.0, 101.0],
            "close": [101.0, 102.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "volume": [1000.0, 1000.0],
        })
        result = check_rubbing_strategy(df)
        assert result["buy_signal"] is False
