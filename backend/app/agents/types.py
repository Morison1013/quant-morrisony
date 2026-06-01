"""
多 Agent 协作 — 共享状态定义。

使用 TypedDict（LangGraph 原生支持）而非 dataclass。
"""

from typing import Optional, TypedDict


class StockScanResult(TypedDict, total=False):
    """单只股票扫描结果。"""
    code: str
    name: str
    close: float
    latest_date: str
    strategy_score: int
    matched_strategies: list[str]
    checks: dict[str, bool]


class StrategyResult(TypedDict, total=False):
    """单个策略 Agent 的扫描结果。"""
    strategy_key: str
    strategy_name: str
    matched_stocks: list[StockScanResult]
    total_scanned: int
    error: Optional[str]


class ScanState(TypedDict, total=False):
    """
    LangGraph 工作流的共享状态。

    流程：
    1. Fetcher Agent 填充 stock_list
    2. Strategy Runner 并行执行策略扫描，填充 strategy_results
    3. Merge Agent 汇总到 final_ranking
    """
    # 输入
    strategies: list[str]
    stock_list: list[dict]

    # 中间结果
    strategy_results: dict[str, StrategyResult]

    # 最终输出
    final_ranking: list[dict]
    total_scanned: int
    total_matched: int
    total_skipped: int
    elapsed_ms: int
    error: Optional[str]
