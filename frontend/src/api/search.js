import { apiPost } from './client.js'

/**
 * 资源库检索
 * POST /api/search
 */
export function searchResources({ query, userType = 'visitor', topK = 5, minConfidence = 0.7 }) {
  return apiPost('/api/search', { query, user_type: userType, top_k: topK, min_confidence: minConfidence })
}

/**
 * 平台 v2 检索（PostgreSQL + Chroma v2）
 * POST /api/v1/platform/search
 * 若后端未配置 DATABASE_URL 会返回 503，调用方负责降级处理
 */
export function searchPlatform({ query, userType = 'visitor', topK = 5, minConfidence = 0.7 }) {
  return apiPost('/api/v1/platform/search', { query, user_type: userType, top_k: topK, min_confidence: minConfidence })
}
