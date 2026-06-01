"""
RAG 知识库 API 路由。

遵循现有 API 设计模式：
- 每个路由对应独立功能
- 使用纯函数服务层
- 返回标准 Schema
"""

from fastapi import APIRouter, Query, BackgroundTasks

from app.schemas.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
    IndexStatusResponse,
    IndexRequest,
    IndexResponse,
    QueryCategory,
)
from app.services.rag.rag_pipeline import rag_query, get_index_status
from app.services.rag.indexer import index_documents
from app.services.rag.retriever import get_suggestions

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RAGQueryResponse)
async def query_knowledge(request: RAGQueryRequest):
    """
    RAG 知识库问答接口。

    流程：
    1. 用户问题 Embedding
    2. ChromaDB 向量检索
    3. 上下文构建 + LLM 生成
    4. 返回答案 + 检索文档
    """
    return await rag_query(
        query=request.query,
        category=request.category,
        top_k=request.top_k,
        session_id=request.session_id,
    )


@router.get("/status", response_model=IndexStatusResponse)
def get_knowledge_status():
    """获取知识库索引状态。"""
    status = get_index_status()
    return IndexStatusResponse(**status)


@router.post("/index", response_model=IndexResponse)
async def trigger_index(
    request: IndexRequest,
    background_tasks: BackgroundTasks,
):
    """
    触发文档索引（后台执行）。

    Args:
        categories: 指定分类索引（空则全量）
        force_reindex: 强制重建索引
    """
    # 直接执行索引（小型文档库，不需要后台）
    result = await index_documents(
        categories=request.categories,
        force_reindex=request.force_reindex,
    )
    return IndexResponse(**result)


@router.get("/suggestions")
def get_query_suggestions(
    prefix: str = Query(default="", description="查询前缀"),
    limit: int = Query(default=5, ge=1, le=10),
):
    """获取查询建议（基于预设热门问题）。"""
    return {"suggestions": get_suggestions(prefix, limit)}