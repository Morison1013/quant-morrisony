/**
 * RAG 知识库问答 — 类型定义
 */

/** 查询分类 */
export type QueryCategory = "strategy" | "concept" | "guide" | "faq" | "general";

/** 检索到的文档 */
export interface RetrievedDocument {
  doc_id: string;
  title: string;
  content: string;
  category: string;
  score: number;
  source: string;
}

/** 聊天消息 */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  retrieved_docs?: RetrievedDocument[];
  confidence?: number;
  elapsed_ms?: number;
  timestamp: Date;
}

/** RAG 查询请求 */
export interface RAGQueryRequest {
  query: string;
  category?: QueryCategory;
  top_k?: number;
  session_id?: string;
}

/** RAG 查询响应 */
export interface RAGQueryResponse {
  answer: string;
  retrieved_docs: RetrievedDocument[];
  confidence: number;
  elapsed_ms: number;
  session_id: string;
  suggestions: string[];
}

/** 索引状态 */
export interface IndexStatus {
  total_docs: number;
  categories: Record<string, number>;
  last_indexed: string | null;
  chroma_path: string;
  embedding_model: string;
  status: string;
}