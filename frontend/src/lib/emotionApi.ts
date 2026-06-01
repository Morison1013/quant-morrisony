import axios from "axios";
import type { EmotionSnapshot } from "./emotionTypes";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const emotionApi = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

/** 获取情绪快照 */
export async function fetchEmotionSnapshot(): Promise<EmotionSnapshot> {
  const { data } = await emotionApi.get<EmotionSnapshot>("/emotion/snapshot");
  return data;
}

/** 手动刷新情绪数据 */
export async function refreshEmotionData(): Promise<EmotionSnapshot> {
  const { data } = await emotionApi.get<EmotionSnapshot>("/emotion/refresh");
  return data;
}
