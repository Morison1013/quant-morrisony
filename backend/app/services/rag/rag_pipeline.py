"""
RAG 主流程：检索 + 生成。

遵循现有 strategy.py 的设计风格：纯函数、清晰管道、结构化返回。
"""

import time
import uuid
from typing import Optional

from app.config import settings
from app.schemas.rag import (
    RAGQueryResponse,
    RetrievedDocument,
    QueryCategory,
)
from app.services.rag.embedding import get_single_embedding
from app.services.rag.vectorstore import query_similar
from app.services.rag.generator import generate_answer
from app.services.rag.retriever import get_suggestions
from app.services.rag.indexer import get_index_status_internal


async def rag_query(
    query: str,
    category: Optional[QueryCategory] = None,
    top_k: int = 3,
    session_id: Optional[str] = None,
) -> RAGQueryResponse:
    """
    RAG 查询主流程。

    Steps:
    1. 问题 Embedding
    2. ChromaDB 检索
    3. 构建 Context
    4. LLM 生成答案
    5. 返回结果
    """
    start_time = time.time()

    # 生成/复用 session_id
    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    # Step 1: Embedding
    try:
        query_embedding = await get_single_embedding(query)
    except Exception as e:
        return RAGQueryResponse(
            answer=f"生成 Embedding 失败：{str(e)}",
            retrieved_docs=[],
            confidence=0.0,
            elapsed_ms=int((time.time() - start_time) * 1000),
            session_id=session_id,
            suggestions=get_suggestions(),
        )

    # Step 2: 向量检索
    category_filter = category.value if category else None
    retrieved = query_similar(
        query_embedding=query_embedding,
        top_k=top_k,
        category_filter=category_filter,
    )

    # 转换为 Schema 格式
    retrieved_docs = [
        RetrievedDocument(
            doc_id=doc["doc_id"],
            title=doc["title"],
            content=doc["content"][:300] + "..." if len(doc["content"]) > 300 else doc["content"],
            category=doc["category"],
            score=doc["score"],
            source=doc["source"],
        )
        for doc in retrieved
    ]

    # Step 3: 构建上下文
    context = _build_context(retrieved)

    # Step 4: LLM 生成
    answer, confidence = await generate_answer(
        query=query,
        context=context,
    )

    # Step 5: 生成建议问题
    suggestions = get_suggestions(query, 3)

    elapsed_ms = int((time.time() - start_time) * 1000)

    return RAGQueryResponse(
        answer=answer,
        retrieved_docs=retrieved_docs,
        confidence=confidence,
        elapsed_ms=elapsed_ms,
        session_id=session_id,
        suggestions=suggestions,
    )


def _build_context(docs: list) -> str:
    """
    构建 RAG 上下文。

    格式化检索文档，限制总长度。
    """
    context_parts = []
    total_length = 0

    for doc in docs:
        # 使用完整内容构建上下文（而非截断版）
        full_content = doc.content if len(doc.content) <= 300 else doc.content[:-3]  # 去掉省略号

        part = f"【{doc.title}】\n{full_content}\n"
        if total_length + len(part) > settings.RAG_MAX_CONTEXT_LENGTH:
            break
        context_parts.append(part)
        total_length += len(part)

    context = "\n---\n".join(context_parts)
    return context


def get_index_status() -> dict:
    """获取索引状态。"""
    return get_index_status_internal()