#!/usr/bin/env python
"""
RAG 知识库索引脚本。

使用方法：
    python scripts/index_knowledge.py           # 正常索引
    python scripts/index_knowledge.py --force   # 强制重建索引
"""

import asyncio
import sys
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag.indexer import index_documents


async def main():
    force = "--force" in sys.argv or "-f" in sys.argv

    print("=" * 50)
    print("RAG 知识库索引脚本")
    print("=" * 50)
    print(f"强制重建: {force}")
    print()

    result = await index_documents(force_reindex=force)

    print(f"索引状态: {result['status']}")
    print(f"文档数量: {result['indexed_count']}")
    print(f"耗时: {result['elapsed_ms']}ms")
    print()

    if result["indexed_count"] > 0:
        print("✅ 知识库索引完成！")
    else:
        print("⚠️ 未索引任何文档，请检查 docs/knowledge 目录")


if __name__ == "__main__":
    asyncio.run(main())