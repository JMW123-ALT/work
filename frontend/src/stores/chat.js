import { defineStore } from 'pinia'
import { ref } from 'vue'
import { streamChat } from '@/api/chat.js'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([]) // [{ id, role: 'user'|'assistant', content, status? }]
  const isStreaming = ref(false)
  const statusText = ref('')
  const activeConversationId = ref(null)

  function addMessage(role, content, extra = {}) {
    const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`
    messages.value.push({ id, role, content, ...extra })
    if (messages.value.length > 40) messages.value = messages.value.slice(-40)
    return id
  }

  function updateMessage(id, patch) {
    const idx = messages.value.findIndex(m => m.id === id)
    if (idx !== -1) Object.assign(messages.value[idx], patch)
  }

  /** 获取最近 10 条用于 history 参数 */
  function getHistory() {
    return messages.value
      .filter(m => m.role !== 'system' && m.content)
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }))
  }

  async function sendMessage(query, userType = 'visitor') {
    if (!query.trim() || isStreaming.value) return

    addMessage('user', query)
    const assistantId = addMessage('assistant', '', { status: 'streaming' })
    isStreaming.value = true
    statusText.value = ''

    let accumulated = ''

    await streamChat(
      { query, userType, history: getHistory() },
      {
        onStart() { statusText.value = '生成中...' },
        onDelta(chunk) {
          accumulated += chunk
          updateMessage(assistantId, { content: accumulated })
        },
        onFinal(payload) {
          statusText.value = payload.evidence_count
            ? `已参考 ${payload.evidence_count} 条资料`
            : '直接回答'
          updateMessage(assistantId, { content: accumulated || payload.final_answer || '' })
        },
        onError(err) {
          statusText.value = '生成中断'
          updateMessage(assistantId, {
            content: accumulated || `生成失败：${err.message}`,
            status: 'error',
          })
        },
        onDone() {
          updateMessage(assistantId, { status: 'done' })
        },
      }
    )

    isStreaming.value = false
  }

  function clearHistory() {
    messages.value = []
    statusText.value = ''
  }

  return { messages, isStreaming, statusText, activeConversationId, sendMessage, clearHistory }
})
