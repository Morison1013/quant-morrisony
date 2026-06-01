"""
文档索引服务。

扫描 docs/knowledge 目录，将 Markdown 文档索引到 ChromaDB。
"""

import json
import time
import re
from pathlib import Path
from typing import Optional, List, Dict

from app.config import settings
from app.services.rag.embedding import get_embeddings
from app.services.rag.vectorstore import add_documents, reset_collection, get_collection_stats


# 知识库文档路径（绝对路径）
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent.parent.parent / settings.KNOWLEDGE_PATH


async def index_documents(
    categories: Optional[List[str]] = None,
    force_reindex: bool = False,
) -> Dict:
    """
    索引知识库文档。

    Args:
        categories: 指定分类索引（空则全量）
        force_reindex: 强制重建索引

    Returns:
        索引结果统计
    """
    start_time = time.time()

    # 强制重建时重置 Collection
    if force_reindex:
        reset_collection()

    # 扫描文档
    docs = _scan_documents(categories)

    if not docs:
        return {
            "indexed_count": 0,
            "elapsed_ms": int((time.time() - start_time) * 1000),
            "status": "no_documents",
        }

    # 批量生成 Embedding（分批处理，避免超限）
    batch_size = 10
    all_embeddings = []

    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        texts = [doc["content"] for doc in batch]
        embeddings = await get_embeddings(texts)
        all_embeddings.extend(embeddings)

    # 写入 ChromaDB
    add_documents(docs, all_embeddings)

    # 记录索引元数据
    _save_index_meta(docs, start_time)

    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "indexed_count": len(docs),
        "elapsed_ms": elapsed_ms,
        "status": "completed",
    }


def _scan_documents(categories: Optional[List[str]] = None) -> List[Dict]:
    """
    扫描知识库目录，提取文档。

    Returns:
        文档列表
    """
    docs = []

    if not KNOWLEDGE_DIR.exists():
        print(f"知识库目录不存在: {KNOWLEDGE_DIR}")
        return docs

    # 分类目录映射
    category_dirs = ["strategies", "concepts", "guides", "faq"]

    for cat_dir in category_dirs:
        # 过滤分类
        if categories and cat_dir not in categories:
            continue

        cat_path = KNOWLEDGE_DIR / cat_dir
        if not cat_path.exists():
            continue

        for md_file in cat_path.glob("*.md"):
            # 跳过索引文件
            if md_file.stem == "index":
                continue

            # 读取文档
            content = md_file.read_text(encoding="utf-8")

            # 提取标题（从第一个 # 行）
            title = _extract_title(content, md_file.stem)

            # 清理内容（移除 Markdown 格式）
            clean_content = _clean_markdown(content)

            # 分块处理（长文档分段）
            chunks = _split_content(clean_content, max_length=800)

            for i, chunk in enumerate(chunks):
                doc_id = f"{md_file.stem}_{i}" if len(chunks) > 1 else md_file.stem
                docs.append({
                    "id": doc_id,
                    "title": title,
                    "content": chunk,
                    "category": cat_dir,
                    "source": str(md_file.relative_to(KNOWLEDGE_DIR.parent.parent)),
                })

    return docs


def _extract_title(content: str, default: str) -> str:
    """从 Markdown 内容提取标题。"""
    for line in content.split("\n"):
        if line.startswith("# "):
            # 提取策略名称部分
            title = line[2:].strip()
            # 处理 "策略名称：XXX" 格式
            if "：" in title or ":" in title:
                parts = re.split(r"[：:]", title)
                if len(parts) > 1:
                    return parts[-1].strip()
            return title
    return default


def _clean_markdown(content: str) -> str:
    """清理 Markdown 格式。"""
    # 移除代码块
    content = re.sub(r"```[\s\S]*?```", "", content)
    # 移除链接但保留文本
    content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
    # 移除表格分隔行
    content = re.sub(r"^\|[-:]+\|\s*$", "", content, flags=re.MULTILINE)
    # 移除多余空行
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _split_content(content: str, max_length: int = 800) -> List[str]:
    """长文档分段。"""
    if len(content) <= max_length:
        return [content]

    chunks = []
    paragraphs = content.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def _save_index_meta(docs: List[Dict], start_time: float):
    """保存索引元数据。"""
    cache_dir = Path(__file__).parent.parent.parent.parent / "data" / "knowledge_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "last_indexed": time.strftime("%Y-%m-%d %H:%M:%S"),
        "indexed_count": len(docs),
        "elapsed_seconds": time.time() - start_time,
        "categories": list(set(doc["category"] for doc in docs)),
    }

    meta_file = cache_dir / "index_meta.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def get_index_status_internal() -> Dict:
    """获取索引状态（内部使用）。"""
    stats = get_collection_stats()

    # 获取最后索引时间
    cache_file = Path(__file__).parent.parent.parent.parent / "data" / "knowledge_cache" / "index_meta.json"
    last_indexed = None
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            meta = json.load(f)
            last_indexed = meta.get("last_indexed")

    return {
        "total_docs": stats["total_docs"],
        "categories": stats["categories"],
        "last_indexed": last_indexed,
        "chroma_path": settings.CHROMA_PATH,
        "embedding_model": settings.EMBEDDING_MODEL,
        "status": "ready" if stats["total_docs"] > 0 else "empty",
    }