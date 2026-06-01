"""
LLM 生成服务 - DeepSeek API。

遵循现有 API 调用风格（httpx）。
"""

import httpx
from typing import Tuple

from app.config import settings


SYSTEM_PROMPT = """你是 Quant_Morrisony 量化交易系统的智能助手。

你的职责是：
1. 解释系统中的技术指标和交易策略
2. 指导用户使用系统功能
3. 回答量化交易相关问题

回答要求：
- 基于提供的知识库内容回答
- 语言简洁专业，使用中文
- 如实告知知识库中没有的信息
- 适当引用具体策略名称和参数"""


async def generate_answer(
    query: str,
    context: str,
) -> Tuple[str, float]:
    """
    使用 DeepSeek API 生成答案。

    Args:
        query: 用户问题
        context: 检索到的上下文

    Returns:
        (答案, 置信度)
    """
    if not context:
        return "抱歉，知识库中没有找到相关信息。请尝试换个问题或查看系统文档。", 0.0

    if not settings.DEEPSEEK_API_KEY:
        return "系统未配置 DeepSeek API Key，无法生成回答。请联系管理员配置。", 0.0

    # 构建 prompt
    prompt = f"""参考知识库内容回答用户问题。

知识库内容：
{context}

用户问题：{query}

请基于以上知识库内容，简洁准确地回答问题（不超过300字）。"""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3,  # 低温度保证稳定输出
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            answer = data["choices"][0]["message"]["content"]

            # 置信度估算（基于上下文长度）
            confidence = 0.85 if len(context) > 500 else 0.6

            return answer, confidence

        except httpx.HTTPStatusError as e:
            error_msg = str(e.response.status_code)
            if e.response.status_code == 401:
                return "API Key 无效，请检查配置。", 0.0
            elif e.response.status_code == 429:
                return "API 调用频率超限，请稍后重试。", 0.0
            else:
                return f"API 调用失败 ({error_msg})，请稍后重试。", 0.0
        except Exception as e:
            return f"生成回答时出错：{str(e)}", 0.0