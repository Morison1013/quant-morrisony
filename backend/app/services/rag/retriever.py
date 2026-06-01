"""
检索辅助服务。
"""

from typing import List

# 预设建议问题
DEFAULT_SUGGESTIONS = [
    "均线多头策略怎么用？",
    "MACD金叉信号的条件是什么？",
    "什么是揉搓线洗盘？",
    "如何使用全市场扫描？",
    "打板情绪监控怎么看？",
]


def get_suggestions(prefix: str = "", limit: int = 5) -> List[str]:
    """
    获取查询建议。

    Args:
        prefix: 查询前缀（暂不使用）
        limit: 返回数量

    Returns:
        建议问题列表
    """
    # 简单实现：返回预设建议
    # 未来可扩展：基于历史查询或热门问题
    return DEFAULT_SUGGESTIONS[:limit]