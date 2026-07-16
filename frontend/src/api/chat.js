import { apiGet, apiPost, streamPost } from './client.js'

/** GET /api/health */
export const checkHealth = () => apiGet('/api/health')

/**
 * 流式问答（AI问答页面）
 * POST /api/v1/chat/stream
 */
export function streamChat({ query, userType = 'visitor', topK = 5, minConfidence = 0.7, history = [] }, handlers) {
  return streamPost('/api/v1/chat/stream', {
    query,
    user_type: userType,
    top_k: topK,
    min_confidence: minConfidence,
    history: history.slice(-10),
  }, handlers)
}

/**
 * 文创 Agent（阻塞式）
 * POST /api/chat
 */
export function runAgent({ query, userType = 'visitor', topK = 5, minConfidence = 0.7 }) {
  return apiPost('/api/chat', {
    query,
    user_type: userType,
    top_k: topK,
    min_confidence: minConfidence,
  })
}
