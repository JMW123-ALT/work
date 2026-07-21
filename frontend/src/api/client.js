/**
 * API 基础封装
 * - apiGet / apiPost / apiUpload / streamPost
 * - 统一错误处理，后端不可用时给出清晰提示
 */

const BASE = ''

export async function apiGet(path) {
  const res = await fetch(BASE + path)
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.message || data.detail || `GET ${path} → ${res.status}`)
  }
  return res.json()
}

export async function apiPost(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.message || data.detail || `POST ${path} → ${res.status}`)
  return data
}

export async function apiDelete(path) {
  const res = await fetch(BASE + path, { method: 'DELETE' })
  if (res.status === 204) return {}
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.message || data.detail || `DELETE ${path} → ${res.status}`)
  return data
}

export async function apiUpload(path, formData) {
  const res = await fetch(BASE + path, { method: 'POST', body: formData })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.message || data.detail || `UPLOAD ${path} → ${res.status}`)
  return data
}

/**
 * streamPost — SSE 流式接口
 * @param {string} path
 * @param {object} body
 * @param {{
 *   onStart?: () => void,
 *   onDelta: (content: string) => void,
 *   onFinal?: (payload: object) => void,
 *   onError?: (err: Error) => void,
 *   onDone?: () => void,
 * }} handlers
 */
export async function streamPost(path, body, handlers) {
  let res
  try {
    res = await fetch(BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch (e) {
    handlers.onError?.(new Error('无法连接到服务器，请检查后端是否启动'))
    return
  }

  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => ({}))
    handlers.onError?.(new Error(data.message || data.detail || '请求失败'))
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      // 按双换行分割 SSE 事件块
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() // 最后一块可能不完整，留着等下次
      for (const block of blocks) {
        if (!block.trim()) continue
        let eventType = 'message'
        let dataStr = ''
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) eventType = line.slice(6).trim()
          if (line.startsWith('data:')) dataStr += line.slice(5).trim()
        }
        if (!dataStr) continue
        let payload
        try { payload = JSON.parse(dataStr) } catch { continue }
        if (eventType === 'start') handlers.onStart?.()
        if (eventType === 'delta') handlers.onDelta(payload.content || '')
        if (eventType === 'final') handlers.onFinal?.(payload)
        if (eventType === 'done') handlers.onDone?.()
        if (eventType === 'error') handlers.onError?.(new Error(payload.message || '流式生成失败'))
      }
    }
  } catch (e) {
    handlers.onError?.(e)
  }
}
