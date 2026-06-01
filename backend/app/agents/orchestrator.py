"""
多 Agent 协作 — 并行扫描执行器。

基于原有的 scanner.py 逻辑，改造为多 Agent 并行架构：
- 每个策略是一个独立 Agent
- 单策略直接运行（复用原有逻辑）
- 多策略时各策略并行执行，最后交叉验证汇总
"""

import time

from app.agents.types import ScanState, StrategyResult, StockScanResult
from app.agents.strategy_agents import AGENT_REGISTRY, get_all_stock_codes


# ────────────────────────────────────────────
# 单策略扫描（复用原有 scanner.py 的逻辑）
# ────────────────────────────────────────────

def _scan_single_strategy(strategy_key: str, stock_list: list[dict]) -> StrategyResult:
    """
    使用原有 scanner.py 的高性能逻辑扫描单只股票。
    复用 _check_stock_fast 的并发 + 缓存机制。
    """
    from app.services.scanner import _fast_fetch, _parse_fast_data, MIN_DATA_DAYS
    from app.services.strategy import run_strategy_pipeline
    from app.agents.strategy_agents import AGENT_REGISTRY

    agent = AGENT_REGISTRY[strategy_key]

    matched = []
    total = 0

    for stock in stock_list:
        code = stock["code"]
        name = stock.get("name", "")
        total += 1

        raw_data = _fast_fetch(code)
        if not raw_data:
            continue

        df = _parse_fast_data(raw_data)
        if df is None or len(df) < MIN_DATA_DAYS:
            continue

        df = run_strategy_pipeline(df)

        if agent.scan_stock(code, name, df):
            latest_close = round(float(df.iloc[-1]["close"]), 2)
            latest_date = str(df.iloc[-1]["date"].date())
            matched.append({
                "code": code,
                "name": name,
                "close": latest_close,
                "latest_date": latest_date,
                "strategy_score": 0,
                "matched_strategies": [strategy_key],
                "checks": {strategy_key: True},
            })

    return {
        "strategy_key": strategy_key,
        "strategy_name": agent.name,
        "matched_stocks": matched,
        "total_scanned": total,
    }


# ────────────────────────────────────────────
# 多策略并行执行
# ────────────────────────────────────────────

def run_strategies_parallel(strategies: list[str], stock_list: list[dict]) -> dict:
    """
    并行执行所有选中的策略 Agent。

    单策略：直接运行（避免额外开销）
    多策略：使用原有 scanner 的高性能并发机制
    """
    valid_keys = [k for k in strategies if k in AGENT_REGISTRY]
    if not valid_keys:
        return {}

    # 单策略直接运行
    if len(valid_keys) == 1:
        result = _scan_single_strategy(valid_keys[0], stock_list)
        return {valid_keys[0]: result}

    # 多策略：每个策略在独立线程中并行
    from concurrent.futures import ThreadPoolExecutor, as_completed

    strategy_results: dict = {}

    def run_one(key: str) -> dict:
        return _scan_single_strategy(key, stock_list)

    with ThreadPoolExecutor(max_workers=len(valid_keys)) as executor:
        futures = {executor.submit(run_one, key): key for key in valid_keys}
        for future in as_completed(futures):
            key = futures[future]
            try:
                result = future.result(timeout=600)
                strategy_results[key] = result
            except Exception as e:
                strategy_results[key] = {
                    "strategy_key": key,
                    "strategy_name": key,
                    "matched_stocks": [],
                    "total_scanned": 0,
                    "error": str(e),
                }

    return strategy_results


# ────────────────────────────────────────────
# Merge（汇总排序 + 交叉验证 + 打分）
# ────────────────────────────────────────────

def merge_strategy_results(strategy_results: dict, selected_strategies: list[str]) -> list[dict]:
    """
    汇总所有策略结果，计算综合打分，排序。

    交叉验证逻辑：
    - 匹配越多策略 → 信号越强 → 打分越高
    - 匹配全部策略 → 额外加分（共振信号）
    """
    total_selected = len(selected_strategies)

    # 合并：code → {策略列表 + 股票信息}
    stock_map: dict[str, dict] = {}

    for strat_key, result in strategy_results.items():
        error = result.get("error")
        if error:
            continue
        for stock in result.get("matched_stocks", []):
            code = stock["code"]
            if code not in stock_map:
                stock_map[code] = {
                    "code": code,
                    "name": stock.get("name", ""),
                    "close": stock.get("close", 0),
                    "latest_date": stock.get("latest_date", ""),
                    "matched_strategies": [],
                    "checks": {},
                }
            stock_map[code]["matched_strategies"].append(strat_key)
            stock_map[code]["checks"].update(stock.get("checks", {}))

    # 交叉验证 + 打分
    final_ranking = []
    for code, info in stock_map.items():
        match_count = len(info["matched_strategies"])

        # 基础分：每匹配一个策略 +20
        score = match_count * 20

        # 共振奖励：匹配全部策略
        if match_count == total_selected and total_selected > 1:
            score += 30

        # 策略权重加成
        weights = {
            "ma_bullish": 1.0,
            "macd_golden": 1.2,
            "arbitrage": 0.8,
            "rubbing": 1.0,
        }
        weighted_bonus = sum(
            10 * weights.get(s, 1.0)
            for s in info["matched_strategies"]
        )
        score += int(weighted_bonus)
        score = min(100, score)

        final_ranking.append({
            "code": info["code"],
            "name": info["name"],
            "close": info["close"],
            "latest_date": info["latest_date"],
            "strategy_score": score,
            "matched_strategies": info["matched_strategies"],
            "checks": info["checks"],
        })

    final_ranking.sort(key=lambda x: (-x["strategy_score"], x["code"]))
    return final_ranking


# ────────────────────────────────────────────
# LangGraph 工作流定义（用于可视化/文档）
# ────────────────────────────────────────────

def build_scan_workflow():
    """
    构建全市场扫描的 LangGraph 工作流（仅用于可视化）。

    图结构：
    START → fetcher → run_strategies → merge → END

    实际执行通过 multi_agent_scan 函数。
    """
    from langgraph.graph import StateGraph, START, END

    def fetcher(state: ScanState) -> dict:
        return {"stock_list": get_all_stock_codes()}

    def runner(state: ScanState) -> dict:
        results = run_strategies_parallel(
            state.get("strategies", []),
            state.get("stock_list", []),
        )
        return {"strategy_results": results}

    def merger(state: ScanState) -> dict:
        ranking = merge_strategy_results(
            state.get("strategy_results", {}),
            state.get("strategies", []),
        )
        strategy_results = state.get("strategy_results", {})
        total_scanned = max(
            (r.get("total_scanned", 0) for r in strategy_results.values() if not r.get("error")),
            default=0,
        )
        return {
            "final_ranking": ranking,
            "total_scanned": total_scanned,
            "total_matched": len(ranking),
            "total_skipped": total_scanned - len(ranking),
        }

    workflow = StateGraph(ScanState)
    workflow.add_node("fetcher", fetcher)
    workflow.add_node("run_strategies", runner)
    workflow.add_node("merge", merger)
    workflow.add_edge(START, "fetcher")
    workflow.add_edge("fetcher", "run_strategies")
    workflow.add_edge("run_strategies", "merge")
    workflow.add_edge("merge", END)

    return workflow.compile()


# ────────────────────────────────────────────
# 高层 API
# ────────────────────────────────────────────

def multi_agent_scan(strategies: list[str], progress_callback=None) -> dict:
    """
    多 Agent 并行扫描入口。

    对于单策略，直接复用原有 scan_stocks（已经高度优化）。
    对于多策略，各策略并行执行，最后交叉验证汇总。

    Args:
        strategies: 选中的策略 key 列表

    Returns:
        与原有 scan_stocks 兼容的结果 dict
    """
    if not strategies:
        return {
            "total": 0, "matched": 0, "skipped": 0,
            "elapsed_ms": 0, "results": [],
            "error": "请至少选择一个策略",
        }

    valid_strategies = [s for s in strategies if s in AGENT_REGISTRY]
    invalid = [s for s in strategies if s not in AGENT_REGISTRY]

    if not valid_strategies:
        return {
            "total": 0, "matched": 0, "skipped": 0,
            "elapsed_ms": 0, "results": [],
            "error": f"未知策略: {invalid}",
        }

    # 单策略：直接复用原有 scan_stocks（已高度优化，16 线程并发）
    if len(valid_strategies) == 1:
        from app.services.scanner import scan_stocks
        result = scan_stocks(valid_strategies)
        return result

    # 多策略：并行执行每个策略
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from app.services.scanner import scan_stocks

    overall_start = time.time()

    def run_one(key: str) -> tuple[str, dict]:
        return key, scan_stocks([key])

    strategy_results: dict = {}
    with ThreadPoolExecutor(max_workers=len(valid_strategies)) as executor:
        futures = {executor.submit(run_one, key): key for key in valid_strategies}
        for future in as_completed(futures):
            key = futures[future]
            try:
                strat_key, result = future.result(timeout=600)
                strategy_results[strat_key] = result
            except Exception as e:
                strategy_results[key] = {
                    "total": 0, "matched": 0, "skipped": 0,
                    "elapsed_ms": 0, "results": [],
                    "error": str(e),
                }

    # 交叉验证 + 合并
    final_ranking = merge_strategy_results_for_scan(strategy_results, valid_strategies)

    total_scanned = max(
        (r.get("total", 0) for r in strategy_results.values() if not r.get("error")),
        default=0,
    )
    max_elapsed = max(
        (r.get("elapsed_ms", 0) for r in strategy_results.values() if not r.get("error")),
        default=0,
    )
    overall_ms = int((time.time() - overall_start) * 1000)

    return {
        "total": total_scanned,
        "matched": len(final_ranking),
        "skipped": total_scanned - len(final_ranking),
        "elapsed_ms": max_elapsed,
        "results": final_ranking,
        "error": None,
    }


def merge_strategy_results_for_scan(strategy_results: dict, selected_strategies: list[str]) -> list[dict]:
    """合并多个 scan_stocks 的结果，交叉验证 + 打分。"""
    total_selected = len(selected_strategies)

    stock_map: dict[str, dict] = {}
    for strat_key, result in strategy_results.items():
        for stock in result.get("results", []):
            code = stock["code"]
            if code not in stock_map:
                stock_map[code] = {
                    "code": code,
                    "name": stock.get("name", ""),
                    "close": stock.get("close", 0),
                    "latest_date": stock.get("latest_date", ""),
                    "matched_strategies": [],
                }
            stock_map[code]["matched_strategies"].append(strat_key)

    final_ranking = []
    for code, info in stock_map.items():
        match_count = len(info["matched_strategies"])
        score = match_count * 20

        if match_count == total_selected and total_selected > 1:
            score += 30

        weights = {"ma_bullish": 1.0, "macd_golden": 1.2, "arbitrage": 0.8, "rubbing": 1.0}
        weighted_bonus = sum(10 * weights.get(s, 1.0) for s in info["matched_strategies"])
        score += int(weighted_bonus)
        score = min(100, score)

        final_ranking.append({
            "code": info["code"],
            "name": info["name"],
            "close": info["close"],
            "latest_date": info["latest_date"],
            "strategy_score": score,
            "matched_strategies": info["matched_strategies"],
        })

    final_ranking.sort(key=lambda x: (-x["strategy_score"], x["code"]))
    return final_ranking
