"""
全市场扫描 API 路由。

提供股票扫描接口，用户可勾选策略进行全市场筛选。
支持 SSE 实时进度推送。
"""

import asyncio
import json
import queue
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.schemas.stock import ScanResponse, ScanResultItem
from app.services.scanner import STRATEGY_FLAGS, scan_stocks

router = APIRouter(prefix="/scanner", tags=["scanner"])


def _parse_strategies(**kwargs) -> list:
    """从查询参数提取策略列表"""
    strategies = []
    if kwargs.get("ma_bullish"):
        strategies.append("ma_bullish")
    if kwargs.get("macd_golden"):
        strategies.append("macd_golden")
    if kwargs.get("arbitrage"):
        strategies.append("arbitrage")
    if kwargs.get("rubbing"):
        strategies.append("rubbing")
    # 8个双K线影线策略
    if kwargs.get("continue_down"):
        strategies.append("continue_down")
    if kwargs.get("support_range"):
        strategies.append("support_range")
    if kwargs.get("support_rebound"):
        strategies.append("support_rebound")
    if kwargs.get("short_stop"):
        strategies.append("short_stop")
    if kwargs.get("diverge_start"):
        strategies.append("diverge_start")
    if kwargs.get("diverge_strong"):
        strategies.append("diverge_strong")
    if kwargs.get("strong_support"):
        strategies.append("strong_support")
    if kwargs.get("weak_support"):
        strategies.append("weak_support")
    return strategies


async def _generate_scan_stream(strategies: list):
    """
    SSE 生成器：实时推送扫描进度。
    """
    progress_queue = queue.Queue()

    def sync_progress_callback(current: int, total: int, result: dict):
        """同步回调：将进度放入队列"""
        progress_queue.put({
            "type": "progress",
            "current": current,
            "total": total,
            "percent": int(current / total * 100),
        })
        if result:
            progress_queue.put({"type": "match", "result": result})

    # 在线程池中运行同步扫描
    loop = asyncio.get_event_loop()

    def run_scan():
        return scan_stocks(strategies, progress_callback=sync_progress_callback)

    scan_task = loop.run_in_executor(None, run_scan)

    # 同时处理进度更新
    while not scan_task.done():
        try:
            item = progress_queue.get(timeout=0.1)
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        except queue.Empty:
            await asyncio.sleep(0.05)

    # 处理剩余的进度更新
    while not progress_queue.empty():
        item = progress_queue.get()
        yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    # 获取最终结果
    final_result = await scan_task

    # 发送完成消息
    yield f"data: {json.dumps({
        'type': 'done',
        'total': final_result['total'],
        'matched': final_result['matched'],
        'skipped': final_result['skipped'],
        'elapsed_ms': final_result['elapsed_ms'],
        'results': final_result['results'],
    }, ensure_ascii=False)}\n\n"


@router.get("/scan-stream")
async def scan_market_stream(
    ma_bullish: bool = Query(default=False, description="均线多头排列"),
    macd_golden: bool = Query(default=False, description="月MACD金叉"),
    arbitrage: bool = Query(default=False, description="隔日套利信号"),
    rubbing: bool = Query(default=False, description="揉搓线洗盘"),
    continue_down: bool = Query(default=False, description="中继下跌"),
    support_range: bool = Query(default=False, description="支撑位震荡选方向"),
    support_rebound: bool = Query(default=False, description="支撑位资金抢反弹"),
    short_stop: bool = Query(default=False, description="短期止跌"),
    diverge_start: bool = Query(default=False, description="开始有分歧"),
    diverge_strong: bool = Query(default=False, description="分歧但强势看新高"),
    strong_support: bool = Query(default=False, description="承接力度大只承接不追高"),
    weak_support: bool = Query(default=False, description="承接低可能出现短期顶"),
):
    """
    全市场扫描（SSE 实时进度版）。

    返回 SSE 流：
    - progress: {current, total, percent}
    - match: {result} - 单个匹配结果
    - done: 最终汇总
    """
    strategies = _parse_strategies(
        ma_bullish=ma_bullish, macd_golden=macd_golden, arbitrage=arbitrage, rubbing=rubbing,
        continue_down=continue_down, support_range=support_range, support_rebound=support_rebound,
        short_stop=short_stop, diverge_start=diverge_start, diverge_strong=diverge_strong,
        strong_support=strong_support, weak_support=weak_support,
    )

    if not strategies:
        # 返回错误的 SSE 流
        async def error_stream():
            yield f"data: {json.dumps({'error': '请至少选择一个策略'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    return StreamingResponse(
        _generate_scan_stream(strategies),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/scan", response_model=ScanResponse)
def scan_market(
    ma_bullish: bool = Query(default=False, description="均线多头排列（60/55/30/20/10/5 全向上）"),
    macd_golden: bool = Query(default=False, description="月MACD金叉且周/日未死叉"),
    arbitrage: bool = Query(default=False, description="隔日套利信号（量缩价稳）"),
    rubbing: bool = Query(default=False, description="揉搓线洗盘 BUY 信号"),
    # 8个双K线影线策略
    continue_down: bool = Query(default=False, description="中继下跌（下跌趋势+下影接上影+阴线）"),
    support_range: bool = Query(default=False, description="支撑位震荡选方向（下跌趋势+下影接上影+阳线）"),
    support_rebound: bool = Query(default=False, description="支撑位资金抢反弹（下跌趋势+上影接下影+阳线）"),
    short_stop: bool = Query(default=False, description="短期止跌（下跌趋势+上影接下影+阴线）"),
    diverge_start: bool = Query(default=False, description="开始有分歧（上涨趋势+下影接上影+阴线）"),
    diverge_strong: bool = Query(default=False, description="分歧但强势看新高（上涨趋势+下影接上影+阳线）"),
    strong_support: bool = Query(default=False, description="承接力度大只承接不追高（上涨趋势+上影接下影+阳线）"),
    weak_support: bool = Query(default=False, description="承接低可能出现短期顶（上涨趋势+上影接下影+阴线）"),
):
    """
    全市场扫描（串行版）：返回满足所有选中策略的股票列表。
    结果按 strategy_score 降序排列。
    """
    strategies = _parse_strategies(
        ma_bullish=ma_bullish, macd_golden=macd_golden, arbitrage=arbitrage, rubbing=rubbing,
        continue_down=continue_down, support_range=support_range, support_rebound=support_rebound,
        short_stop=short_stop, diverge_start=diverge_start, diverge_strong=diverge_strong,
        strong_support=strong_support, weak_support=weak_support,
    )

    result = scan_stocks(strategies)

    return ScanResponse(
        total=result["total"],
        matched=result["matched"],
        skipped=result["skipped"],
        elapsed_ms=result["elapsed_ms"],
        results=[ScanResultItem(**r) for r in result.get("results", [])],
        error=result.get("error"),
    )


@router.get("/scan-parallel", response_model=ScanResponse)
def scan_market_parallel(
    ma_bullish: bool = Query(default=False, description="均线多头排列"),
    macd_golden: bool = Query(default=False, description="月MACD金叉"),
    arbitrage: bool = Query(default=False, description="隔日套利信号"),
    rubbing: bool = Query(default=False, description="揉搓线洗盘"),
    # 8个双K线影线策略
    continue_down: bool = Query(default=False, description="中继下跌"),
    support_range: bool = Query(default=False, description="支撑位震荡选方向"),
    support_rebound: bool = Query(default=False, description="支撑位资金抢反弹"),
    short_stop: bool = Query(default=False, description="短期止跌"),
    diverge_start: bool = Query(default=False, description="开始有分歧"),
    diverge_strong: bool = Query(default=False, description="分歧但强势看新高"),
    strong_support: bool = Query(default=False, description="承接力度大只承接不追高"),
    weak_support: bool = Query(default=False, description="承接低可能出现短期顶"),
):
    """
    全市场扫描（多 Agent 并行版）。

    单策略：直接复用原有 scan_stocks（已高度优化，16 线程并发）
    多策略：每个策略独立并行执行，最后交叉验证汇总排序
    扫描速度 ≈ 最慢单个策略的时间（而非累加）
    """
    from app.agents.orchestrator import multi_agent_scan

    strategies = _parse_strategies(
        ma_bullish=ma_bullish, macd_golden=macd_golden, arbitrage=arbitrage, rubbing=rubbing,
        continue_down=continue_down, support_range=support_range, support_rebound=support_rebound,
        short_stop=short_stop, diverge_start=diverge_start, diverge_strong=diverge_strong,
        strong_support=strong_support, weak_support=weak_support,
    )

    result = multi_agent_scan(strategies)

    return ScanResponse(
        total=result["total"],
        matched=result["matched"],
        skipped=result["skipped"],
        elapsed_ms=result["elapsed_ms"],
        results=[ScanResultItem(**r) for r in result.get("results", [])],
        error=result.get("error"),
    )


@router.get("/agents")
def list_agents():
    """
    获取所有可用的扫描 Agent 信息。
    """
    from app.agents.strategy_agents import AGENT_REGISTRY

    return {
        "agents": {
            key: {
                "name": agent.name,
                "key": agent.key,
                "description": STRATEGY_FLAGS.get(key, ""),
            }
            for key, agent in AGENT_REGISTRY.items()
        },
        "workflow": "Fetcher → Parallel Strategy Agents → Merge/Verify",
    }


@router.get("/strategies")
def list_strategies():
    """
    获取所有可用的策略标志及描述。
    """
    return {"strategies": STRATEGY_FLAGS}


@router.get("/db-stats")
def db_stats():
    """
    获取本地数据库统计信息。
    """
    from app.services.db import get_db_stats, get_last_refresh

    stats = get_db_stats()
    stats["last_refresh"] = get_last_refresh()
    return stats