"""
RAG 知识库 API Schema 定义。
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class QueryCategory(str, Enum):
    """查询分类"""
    STRATEGY = "strategy"       # 策略相关
    CONCEPT = "concept"         # 基础概念
    GUIDE = "guide"             # 操作指南
    FAQ = "faq"                 # 常见问题
    GENERAL = "general"         # 通用查询


class RetrievedDocument(BaseModel):
    """检索到的文档"""
    doc_id: str
    title: str
    content: str
    category: str
    score: float = Field(..., ge=0, le=1, description="相关性得分")
    source: str  # 文档来源路径


class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""
    query: str = Field(..., min_length=2, max_length=500, description="用户问题")
    category: Optional[QueryCategory] = Field(default=None, description="查询分类（可选）")
    top_k: int = Field(default=3, ge=1, le=10, description="检索文档数量")
    session_id: Optional[str] = Field(default=None, description="会话ID")


class RAGQueryResponse(BaseModel):
    """RAG 查询响应"""
    answer: str
    retrieved_docs: list[RetrievedDocument]
    confidence: float = Field(..., ge=0, le=1, description="回答置信度")
    elapsed_ms: int
    session_id: str
    suggestions: list[str] = Field(default_factory=list, description="相关问题建议")


class IndexStatusResponse(BaseModel):
    """索引状态响应"""
    total_docs: int
    categories: dict[str, int]  # 各分类文档数
    last_indexed: Optional[str]
    chroma_path: str
    embedding_model: str
    status: str  # "ready" / "indexing" / "error" / "empty"


class IndexRequest(BaseModel):
    """索引请求"""
    categories: Optional[list[str]] = Field(default=None, description="指定分类（空则全量）")
    force_reindex: bool = Field(default=False, description="强制重建索引")


class IndexResponse(BaseModel):
    """索引响应"""
    indexed_count: int
    elapsed_ms: int
    status: str