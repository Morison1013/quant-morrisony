"""
扫描器模块单元测试。

使用 mock 验证扫描逻辑，不依赖网络请求。
"""

import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch

from app.services.scanner import _check_stock_fast, scan_stocks, _parse_fast_data


def _make_uptrend_df(days: int = 120) -> pd.DataFrame:
    """生成上升趋势数据（满足均线多头）。"""
    np.random.seed(42)
    trend = np.linspace(100.0, 130.0, days)
    noise = np.random.normal(0, 0.5, days)
    close = trend + noise
    high = close + np.abs(np.random.normal(0, 0.3, days))
    low = close - np.abs(np.random.normal(0, 0.3, days))
    open_ = close + np.random.normal(0, 0.2, days)
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


class TestCheckStock:
    """单只股票策略检查测试。"""

    def test_check_ma_bullish_on_uptrend(self):
        """上升趋势应满足均线多头。"""
        df = _make_uptrend_df()
        cache = {}
        with patch("app.services.scanner._fast_fetch") as mock_fetch:
            mock_fetch.return_value = [{"year": d["date"].year, "month": d["date"].month,
                                        "day": d["date"].day, "open": d["open"],
                                        "close": d["close"], "high": d["high"],
                                        "low": d["low"], "vol": d["volume"]}
                                       for _, d in df.iterrows()]
            result = _check_stock_fast("600519", "测试股", ["ma_bullish"], cache)
            assert result is not None
            assert result["code"] == "600519"
            assert "ma_bullish" in result["matched_strategies"]

    def test_check_no_match_when_strategies_not_met(self):
        """默认数据不满足所有策略时返回 None。"""
        df = _make_uptrend_df()
        cache = {}
        with patch("app.services.scanner._fast_fetch") as mock_fetch:
            mock_fetch.return_value = [{"year": d["date"].year, "month": d["date"].month,
                                        "day": d["date"].day, "open": d["open"],
                                        "close": d["close"], "high": d["high"],
                                        "low": d["low"], "vol": d["volume"]}
                                       for _, d in df.iterrows()]
            # 只选 rubbing（默认数据不满足揉搓线）
            result = _check_stock_fast("600519", "测试股", ["rubbing"], cache)
            assert result is None

    def test_check_insufficient_data(self):
        """数据不足 65 天时返回 None。"""
        df = pd.DataFrame({
            "date": pd.date_range("2026-05-01", periods=30, freq="B"),
            "open": [100.0] * 30,
            "high": [101.0] * 30,
            "low": [99.0] * 30,
            "close": [100.5] * 30,
            "volume": [1000.0] * 30,
        })
        cache = {}
        with patch("app.services.scanner._fast_fetch") as mock_fetch:
            mock_fetch.return_value = [{"year": d["date"].year, "month": d["date"].month,
                                        "day": d["date"].day, "open": d["open"],
                                        "close": d["close"], "high": d["high"],
                                        "low": d["low"], "vol": d["volume"]}
                                       for _, d in df.iterrows()]
            result = _check_stock_fast("test001", "测试股", ["ma_bullish"], cache)
            assert result is None

    def test_check_connection_error(self):
        """网络异常时返回 None。"""
        cache = {}
        with patch("app.services.scanner._fast_fetch") as mock_fetch:
            mock_fetch.return_value = None
            result = _check_stock_fast("test001", "测试股", ["ma_bullish"], cache)
            assert result is None


class TestScanStocks:
    """完整扫描流程测试。"""

    def test_scan_empty_strategies_returns_error(self):
        """不选任何策略时返回错误。"""
        result = scan_stocks([])
        assert result["error"] is not None
        assert result["results"] == []

    def test_scan_returns_valid_structure(self):
        """扫描返回正确的数据结构。"""
        result = scan_stocks(["ma_bullish"])
        assert "total" in result
        assert "matched" in result
        assert "skipped" in result
        assert "elapsed_ms" in result
        assert "results" in result
        assert isinstance(result["total"], int)
        assert isinstance(result["matched"], int)
        assert isinstance(result["results"], list)

    def test_scan_results_sorted_by_score(self):
        """结果应按 strategy_score 降序排列。"""
        result = scan_stocks(["ma_bullish"])
        scores = [r["strategy_score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)
