"""
ChromaDB 向量存储管理。

遵循现有 db.py 的设计风格：本地嵌入式存储、简洁 API。
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
from typing import Optional, List, Dict

from app.config import settings


# ChromaDB 路径（绝对路径）
CHROMA_DIR = Path(__file__).parent.parent.parent.parent / settings.CHROMA_PATH


def get_chroma_client() -> chromadb.Client:
    """
    获取 ChromaDB 客户端（持久化存储）。
    """
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        )
    )
    return client


def get_collection() -> chromadb.Collection:
    """
    获取或创建知识库 Collection。
    """
    client = get_chroma_client()

    collection = client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        metadata={
            "embedding_model": settings.EMBEDDING_MODEL,
            "dimension": settings.EMBEDDING_DIMENSION,
            "description": "Quant_Morrisony 策略知识库",
        }
    )
    return collection


def reset_collection() -> chromadb.Collection:
    """重置 Collection（清空所有数据）。"""
    client = get_chroma_client()
    try:
        client.delete_collection(settings.CHROMA_COLLECTION)
    except Exception:
        pass
    return get_collection()


def add_documents(
    docs: List[Dict],
    embeddings: List[List[float]],
) -> int:
    """
    批量添加文档到向量库。

    Args:
        docs: 文档列表，每个文档包含 id, title, content, category, source
        embeddings: 对应的 embedding 向量

    Returns:
        添加的文档数量
    """
    if not docs or not embeddings:
        return 0

    collection = get_collection()

    ids = [doc["id"] for doc in docs]
    metadatas = [
        {
            "title": doc["title"],
            "category": doc["category"],
            "source": doc["source"],
        }
        for doc in docs
    ]
    documents = [doc["content"] for doc in docs]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents,
    )

    return len(docs)


def query_similar(
    query_embedding: List[float],
    top_k: int = 3,
    category_filter: Optional[str] = None,
) -> List[Dict]:
    """
    向量相似度查询。

    Args:
        query_embedding: 查询向量
        top_k: 返回数量
        category_filter: 分类过滤（可选）

    Returns:
        检索结果列表
    """
    collection = get_collection()

    where = None
    if category_filter:
        where = {"category": category_filter}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    # 转换为标准格式
    retrieved = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results["distances"] else 0
            # ChromaDB 使用 L2 距离，转换为相似度 (越大越好)
            # 假设距离范围 0-2，相似度 = 1 - distance/2
            score = max(0, min(1, 1 - distance / 2))

            retrieved.append({
                "doc_id": doc_id,
                "content": results["documents"][0][i] if results["documents"] else "",
                "title": results["metadatas"][0][i].get("title", "") if results["metadatas"] else "",
                "category": results["metadatas"][0][i].get("category", "") if results["metadatas"] else "",
                "source": results["metadatas"][0][i].get("source", "") if results["metadatas"] else "",
                "score": score,
            })

    return retrieved


def get_collection_stats() -> Dict:
    """获取 Collection 统计信息。"""
    collection = get_collection()
    count = collection.count()

    # 获取分类统计
    all_docs = collection.get(include=["metadatas"])
    categories: Dict[str, int] = {}
    if all_docs["metadatas"]:
        for meta in all_docs["metadatas"]:
            cat = meta.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_docs": count,
        "categories": categories,
        "collection_name": collection.name,
    }


def delete_by_category(category: str) -> int:
    """删除指定分类的所有文档。"""
    collection = get_collection()

    # 获取该分类的所有文档 ID
    results = collection.get(
        where={"category": category},
        include=["metadatas"],
    )

    if results["ids"]:
        collection.delete(ids=results["ids"])
        return len(results["ids"])

    return 0