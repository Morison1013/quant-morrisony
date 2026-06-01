"""
Embedding 向量化服务。

使用 OpenAI 兼容接口生成文本 Embedding。
"""

import httpx
from typing import List
from app.config import settings


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    批量获取文本 Embedding。

    Args:
        texts: 文本列表

    Returns:
        Embedding 向量列表
    """
    if not texts:
        return []

    # 使用配置的 Embedding API
    api_key = settings.EMBEDDING_API_KEY or settings.DEEPSEEK_API_KEY
    if not api_key:
        raise ValueError("未配置 Embedding API Key，请在 .env 中设置 EMBEDDING_API_KEY 或 DEEPSEEK_API_KEY")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.EMBEDDING_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.EMBEDDING_MODEL,
                "input": texts,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

    # 按 index 排序返回
    embeddings = [None] * len(texts)
    for item in data["data"]:
        embeddings[item["index"]] = item["embedding"]

    return embeddings


async def get_single_embedding(text: str) -> List[float]:
    """获取单个文本的 Embedding。"""
    embeddings = await get_embeddings([text])
    return embeddings[0]