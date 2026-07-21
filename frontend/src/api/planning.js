/**
 * 图片方案生成 API 封装
 */
import { apiGet, apiPost, apiUpload } from './client.js'

export function listImageModels() {
  return apiGet('/api/v1/planning/image/models')
}

export function generateImagePrompt(payload) {
  return apiPost('/api/v1/planning/image/prompt', payload)
}

export function generateTextToImage(payload) {
  return apiPost('/api/v1/planning/image/text-to-image', payload)
}

export function generateImageToImage(formData) {
  return apiUpload('/api/v1/planning/image/image-to-image', formData)
}
