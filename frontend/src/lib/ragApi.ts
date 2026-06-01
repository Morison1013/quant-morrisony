/**
 * RAG 知识库 — API 调用封装
 */

import axios from "axios";
import type { RAGQueryRequest, RAGQueryResponse, IndexStatus } from "./ragTypes";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const ragApi = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // RAG 查询可能较长
});

/** RAG 知识库问答 */
export async function queryKnowledge(
  request: RAGQueryRequest
): Promise<RAGQueryResponse> {
  const { data } = await ragApi.post<RAGQueryResponse>("/rag/query", request);
  return data;
}

/** 获取索引状态 */
export async function getIndexStatus(): Promise<IndexStatus> {
  const { data } = await ragApi.get<IndexStatus>("/rag/status");
  return data;
}

/** 触发文档索引 */
export async function triggerIndex(
  categories?: string[],
  forceReindex?: boolean
): Promise<{ indexed_count: number; elapsed_ms: number; status: string }> {
  const { data } = await ragApi.post("/rag/index", {
    categories,
    force_reindex: forceReindex,
  });
  return data;
}

/** 获取查询建议 */
export async function getSuggestions(
  prefix: string = "",
  limit: number = 5
): Promise<string[]> {
  const { data } = await ragApi.get<{ suggestions: string[] }>("/rag/suggestions", {
    params: { prefix, limit },
  });
  return data.suggestions;
}