<template>
  <div class="chat-page">
    <!-- 消息列表 -->
    <div class="chat-messages" ref="msgListRef">
      <!-- 空状态 -->
      <div v-if="!chatStore.messages.length" class="chat-empty">
        <div class="chat-empty-icon">🏔️</div>
        <div class="chat-empty-title">你好，我是 AI 文旅助手</div>
        <div class="chat-empty-desc">可以问资料库里的项目、资料和方案，也可以直接连续追问</div>
        <div class="chat-suggestions">
          <el-tag
            v-for="s in suggestions"
            :key="s"
            class="suggestion-tag"
            @click="fillQuery(s)"
          >{{ s }}</el-tag>
        </div>
      </div>

      <!-- 消息气泡 -->
      <template v-else>
        <div
          v-for="msg in chatStore.messages"
          :key="msg.id"
          class="chat-row"
          :class="msg.role"
        >
          <div class="chat-avatar">
            <span v-if="msg.role === 'user'">我</span>
            <span v-else>AI</span>
          </div>
          <div class="chat-bubble" :class="{ streaming: msg.status === 'streaming', error: msg.status === 'error' }">
            <span v-if="msg.status === 'streaming' && !msg.content" class="typing-dots">
              <span /><span /><span />
            </span>
            <span v-else>{{ msg.content }}</span>
          </div>
        </div>
      </template>
    </div>

    <!-- 状态栏 -->
    <div class="chat-status" v-if="chatStore.statusText || chatStore.isStreaming">
      <el-icon class="spin" v-if="chatStore.isStreaming"><Loading /></el-icon>
      <span>{{ chatStore.isStreaming ? '生成中...' : chatStore.statusText }}</span>
    </div>

    <!-- 输入区 -->
    <div class="chat-input-area">
      <div class="chat-input-box">
        <el-input
          v-model="inputText"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 5 }"
          :placeholder="chatStore.isStreaming ? '请等待回答完成...' : '输入问题，Enter 发送，Shift+Enter 换行'"
          :disabled="chatStore.isStreaming"
          @keydown.enter.exact.prevent="send"
          class="chat-textarea"
          resize="none"
        />
        <div class="chat-input-actions">
          <el-button
            link
            type="info"
            size="small"
            @click="chatStore.clearHistory()"
            :disabled="chatStore.isStreaming || !chatStore.messages.length"
            title="清空对话"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
          <el-button
            type="primary"
            :disabled="!inputText.trim() || chatStore.isStreaming"
            @click="send"
            class="send-btn"
          >
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>
      <div class="chat-hint">由 DeepSeek 驱动 · 可召回知识库资料</div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '@/stores/chat.js'
import { useAppStore } from '@/stores/app.js'

const chatStore = useChatStore()
const appStore = useAppStore()
const inputText = ref('')
const msgListRef = ref(null)

const suggestions = [
  '介绍一下文旅融合的核心策略',
  '有哪些适合本地文旅 IP 打造的方法？',
  '帮我分析景区内容营销的常见误区',
]

function fillQuery(text) {
  inputText.value = text
}

async function send() {
  const q = inputText.value.trim()
  if (!q || chatStore.isStreaming) return
  inputText.value = ''
  await chatStore.sendMessage(q, appStore.currentUserType)
}

// 自动滚动到底部
watch(
  () => chatStore.messages,
  async () => {
    await nextTick()
    if (msgListRef.value) {
      msgListRef.value.scrollTop = msgListRef.value.scrollHeight
    }
  },
  { deep: true }
)
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--topbar-height));
  background: var(--color-page-bg);
}

/* 消息区 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0;
  scroll-behavior: smooth;
}

/* 空状态 */
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
  gap: 12px;
  padding: 40px 24px;
}

.chat-empty-icon { font-size: 52px; }

.chat-empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.chat-empty-desc {
  font-size: 14px;
  color: var(--color-text-muted);
}

.chat-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}

.suggestion-tag {
  cursor: pointer;
  border-radius: 16px;
  padding: 4px 14px;
  transition: all var(--transition-base);
}
.suggestion-tag:hover { opacity: 0.8; transform: translateY(-1px); }

/* 消息行 */
.chat-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 24px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.chat-row.user {
  flex-direction: row-reverse;
}

.chat-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.chat-row.user .chat-avatar {
  background: var(--color-primary);
  color: #fff;
}

.chat-row.assistant .chat-avatar {
  background: #e6f4ff;
  color: var(--color-primary);
}

.chat-bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  position: relative;
}

.chat-row.user .chat-bubble {
  background: var(--color-primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-row.assistant .chat-bubble {
  background: var(--color-card-bg);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 4px;
  box-shadow: var(--shadow-card);
}

.chat-bubble.streaming {
  border-color: var(--color-primary) !important;
}

.chat-bubble.error {
  border-color: #ff4d4f !important;
  color: #ff4d4f;
}

/* 打字动画 */
.typing-dots {
  display: flex;
  gap: 4px;
  padding: 2px 0;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ccc;
  animation: bounce 1.2s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}

/* 状态栏 */
.chat-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 24px;
  font-size: 12px;
  color: var(--color-text-muted);
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 输入区 */
.chat-input-area {
  padding: 12px 24px 20px;
  border-top: 1px solid var(--color-border);
  background: var(--color-card-bg);
  flex-shrink: 0;
}

.chat-input-box {
  max-width: 856px;
  margin: 0 auto;
  display: flex;
  gap: 8px;
  align-items: flex-end;
  background: #f7f8fa;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 8px 12px;
  transition: border-color var(--transition-base);
}

.chat-input-box:focus-within {
  border-color: var(--color-primary);
  background: #fff;
}

.chat-textarea { flex: 1; }

:deep(.chat-textarea .el-textarea__inner) {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 4px 0;
  font-size: 14px;
  resize: none;
}

.chat-input-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.send-btn { border-radius: 8px; }

.chat-hint {
  max-width: 856px;
  margin: 6px auto 0;
  font-size: 11px;
  color: var(--color-text-muted);
  text-align: center;
}
</style>
