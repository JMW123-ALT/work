/**
 * 文创 IP 设计接口封装
 */
import { apiPost, streamPost } from './client.js'

// 对话式 IP 形象设计（SSE 流式）
export function ipDesignChatStream(history, handlers) {
  return streamPost('/api/v1/ip/design/chat/stream', { history }, handlers)
}

// 出图：中文 prompt → 英文 → 文生图(text) / 图生图(edit)
export function ipDesignGenerateImage(payload) {
  return apiPost('/api/v1/ip/design/image', payload)
}
