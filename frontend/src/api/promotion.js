/**
 * 宣发相关接口封装
 */
import { apiGet, apiPost, streamPost, streamPostForm } from './client.js'

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

// 公众号推文流式版（SSE，multipart：文本参数 + 上传配图）
export function generateWechatStream(formData, handlers) {
  return streamPostForm('/api/v1/promotion/wechat/stream', formData, handlers)
}

// 抖音短视频脚本流式版（SSE）
export function generateDouyinStream(payload, handlers) {
  return streamPost('/api/v1/promotion/douyin/stream', payload, handlers)
}

// 图片模型列表（复用 planning 的模型接口）
export function listImageModels() {
  return apiGet('/api/v1/planning/image/models')
}

// 图片搜索（Pexels）
export function searchStockImages(query, perPage = 15, page = 1) {
  const q = encodeURIComponent(query)
  return apiGet(`/api/v1/promotion/images/search?query=${q}&per_page=${perPage}&page=${page}`)
}
