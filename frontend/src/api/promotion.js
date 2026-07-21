/**
 * 宣发相关接口封装
 */
import { apiGet, apiPost, streamPost } from './client.js'

// 小红书文案（DeepSeek + 可联网参考爆款）
export function generateXiaohongshu(payload) {
  return apiPost('/api/v1/promotion/xiaohongshu', payload)
}

// 小红书文案流式版（SSE）
export function generateXiaohongshuStream(payload, handlers) {
  return streamPost('/api/v1/promotion/xiaohongshu/stream', payload, handlers)
}

// 小红书配图（复用文生图）
export function generateXiaohongshuImages(payload) {
  return apiPost('/api/v1/promotion/xiaohongshu/images', payload)
}

// 图片模型列表（复用 planning 的模型接口）
export function listImageModels() {
  return apiGet('/api/v1/planning/image/models')
}
