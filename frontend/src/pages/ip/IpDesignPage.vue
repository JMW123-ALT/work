<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">文创设计</div>
      <div class="page-desc">对话式 IP 形象设计：AI 逐步问询需求，确认后生成图片，可持续调整迭代</div>
    </div>

    <div class="ip-layout" ref="layoutRef">
      <!-- 左：对话 -->
      <div class="io-panel work-card left-panel">
        <div class="io-panel-header">
          <el-icon><ChatDotSquare /></el-icon>设计对话
          <div style="flex:1" />
          <el-button link size="small" @click="resetChat"><el-icon><RefreshLeft /></el-icon>重新开始</el-button>
        </div>
        <div class="chat-scroll" ref="chatScroll">
          <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
            <div class="msg-avatar">{{ m.role === 'user' ? '我' : 'AI' }}</div>
            <div class="msg-bubble" v-html="renderBubble(m)" />
          </div>
          <div v-if="chatLoading && !streamingText" class="msg assistant">
            <div class="msg-avatar">AI</div>
            <div class="msg-bubble"><el-icon class="spin"><Loading /></el-icon> 思考中...</div>
          </div>
          <div v-if="streamingText" class="msg assistant">
            <div class="msg-avatar">AI</div>
            <div class="msg-bubble" v-html="renderText(stripBlocks(streamingText))" /><span class="cursor">▋</span>
          </div>
        </div>
        <div class="chat-input">
          <el-input v-model="draft" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="描述你的 IP 需求，或说出要调整的地方（如“背景改成夜景”）…（Enter 发送，Shift+Enter 换行）"
            @keydown.enter.exact.prevent="send" :disabled="chatLoading" />
          <el-button type="primary" :loading="chatLoading" :disabled="!draft.trim()" @click="send">发送</el-button>
        </div>
      </div>

      <!-- 可拖动分隔条 -->
      <div class="gutter" :class="{ dragging }" @mousedown="startDrag"><div class="gutter-bar" /></div>

      <!-- 右：结果 -->
      <div class="io-panel work-card right-panel" :style="{ width: rightWidth + 'px' }">
        <div class="io-panel-header"><el-icon><MagicStick /></el-icon>IP 形象与出图</div>
        <div class="io-panel-body">
          <!-- 空态 -->
          <div v-if="!setting && !promptCn && !images.length" class="wip-placeholder">
            <el-icon><MagicStick /></el-icon>
            <span>跟 AI 聊聊你想要的 IP 形象<br/>确定后这里会显示设定、提示词和图片</span>
          </div>

          <template v-else>
            <!-- IP 形象设定 -->
            <section v-if="setting" class="rs-block">
              <div class="rs-title">🎨 IP 形象设定</div>
              <div v-for="(v, k) in setting" :key="k" class="setting-row" v-show="v && v !== '（未设定）'">
                <span class="setting-key">{{ k }}</span>
                <span class="setting-val">{{ v }}</span>
              </div>
            </section>

            <!-- 变更记录时间线 -->
            <section v-if="changeLog.length" class="rs-block">
              <div class="rs-title">🕘 变更记录</div>
              <div class="timeline">
                <div v-for="(entry, i) in changeLog" :key="i" class="tl-item">
                  <div class="tl-dot" />
                  <div class="tl-body">
                    <div class="tl-head">第 {{ entry.round }} 次调整<span class="tl-time">{{ entry.time }}</span></div>
                    <div v-for="(c, j) in entry.changes" :key="j" class="tl-change">
                      <span class="tl-field">{{ c.field }}</span>
                      <span v-if="c.from" class="tl-from">{{ c.from }}</span>
                      <span v-if="c.from" class="tl-arrow">→</span>
                      <span class="tl-to">{{ c.to }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- 中文 Prompt -->
            <section v-if="promptCn" class="rs-block">
              <div class="rs-title">📝 画面提示词（可编辑，或直接在对话里让 AI 改）</div>
              <el-input v-model="promptCn" type="textarea" :autosize="{ minRows: 3, maxRows: 8 }" />
              <div v-if="promptEn" class="prompt-en">
                <span class="en-label">英文提示词（实际喂给模型）：</span>{{ promptEn }}
              </div>
            </section>

            <!-- 出图控制 -->
            <section v-if="promptCn" class="rs-block">
              <div class="img-controls">
                <span class="ctrl-label">模型</span>
                <el-select v-model="imgModel" size="small" style="width:150px">
                  <el-option v-for="m in models" :key="m" :label="m" :value="m" />
                </el-select>
              </div>
              <div class="img-btns">
                <el-button type="primary" :loading="imgLoading && imgMode==='text'"
                  :disabled="imgLoading" @click="generateImage('text')">
                  <el-icon><Picture /></el-icon>{{ images.length ? '重新生成（文生图）' : '生成图片' }}
                </el-button>
                <el-button v-if="images.length" plain :loading="imgLoading && imgMode==='edit'"
                  :disabled="imgLoading" @click="generateImage('edit')">
                  <el-icon><MagicStick /></el-icon>基于最新图修改（图生图）
                </el-button>
              </div>
              <el-alert v-if="imgError" :title="imgError" type="warning" show-icon :closable="false" style="margin-top:8px">
                <el-button size="small" type="primary" plain @click="retryImage" style="margin-top:6px">
                  <el-icon><RefreshRight /></el-icon>重新生成
                </el-button>
              </el-alert>
            </section>

            <!-- 图片历史画廊 -->
            <section v-if="imgLoading || images.length" class="rs-block">
              <div class="rs-title">🖼️ 出图历史（{{ images.length }}，最新在上）</div>
              <div v-if="imgLoading" class="img-loading">
                <el-icon class="spin"><Loading /></el-icon>
                <span>{{ imgMode === 'edit' ? '基于最新图修改中' : '生成中' }}，出图约 20-30 秒…</span>
                <el-button size="small" plain @click="retryImage">
                  <el-icon><RefreshRight /></el-icon>卡住了？重试
                </el-button>
              </div>
              <div class="gallery">
                <div v-for="(img, i) in reversedImages" :key="img.ts" class="gallery-item">
                  <el-image :src="img.src" fit="contain" class="ip-img"
                    :preview-src-list="reversedImages.map(x => x.src)" :initial-index="i" />
                  <div class="gallery-meta">
                    <el-tag size="small" :type="img.mode === 'edit' ? 'warning' : 'success'">
                      {{ img.mode === 'edit' ? '图生图' : '文生图' }} #{{ images.length - i }}
                    </el-tag>
                    <span v-if="i === 0" class="latest-tag">最新 · 图生图基准</span>
                    <el-button size="small" link @click="downloadImg(img, images.length - i)">
                      <el-icon><Download /></el-icon>下载
                    </el-button>
                  </div>
                </div>
              </div>
            </section>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import { ipDesignChatStream, ipDesignGenerateImage } from '@/api/ip.js'
import { listImageModels } from '@/api/promotion.js'

defineOptions({ name: 'IpDesignPage' })

const OPENING = '你好，我是你的文创 IP 设计助手 🎨 想做一个什么样的 IP 形象？简单说说你的想法，我来帮你一步步完善。'

const messages = ref([{ role: 'assistant', content: OPENING }])
const draft = ref('')
const chatLoading = ref(false)
const streamingText = ref('')
const chatScroll = ref(null)

// 右侧结果
const setting = ref(null)        // 结构化设定对象
const promptCn = ref('')
const promptEn = ref('')
const images = ref([])           // 历史画廊：{ src, mode, promptCn, ts }
const changeLog = ref([])        // 变更记录时间线
let adjustRound = 0

const reversedImages = computed(() => [...images.value].slice().reverse())

// 出图
const models = ref(['gpt-image-2', 'gpt-image-2-pro'])
const imgModel = ref('gpt-image-2')
const imgLoading = ref(false)
const imgMode = ref('text')
const imgError = ref('')

// 可拖动分隔条
const layoutRef = ref(null)
const rightWidth = ref(400)
const dragging = ref(false)

// 触发出图的关键词
const CONFIRM_RE = /(确认|确定).*(生成|出图|画)|生成图片|开始生成|就这样|可以了.*生成/

onMounted(async () => {
  try {
    const res = await listImageModels()
    if (res.models?.length) models.value = res.models
    if (res.default) imgModel.value = res.default
  } catch { /* 兜底 */ }
})

function imgSrc(img) { return img.data_url || img.url || '' }

// ── 拖动分隔条 ──
function startDrag(e) {
  dragging.value = true
  const startX = e.clientX
  const startW = rightWidth.value
  // 以整个布局宽度为界，几乎自由拖动；仅两端各留 80px 防止某侧被拖没
  const total = layoutRef.value?.getBoundingClientRect().width || 1200
  const onMove = (ev) => {
    // 向左拖 → 右侧变宽（左侧变窄）
    const delta = startX - ev.clientX
    rightWidth.value = Math.max(80, Math.min(total - 80, startW + delta))
  }
  const onUp = () => {
    dragging.value = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}
onBeforeUnmount(() => { dragging.value = false })

// 去掉结构化标记块，只保留自然语言对话
// 兼容 AI 偶尔漏写 ===SETTING===、只写 ===PROMPT_CN=== 的情况：
// 从最先出现的任一结构化标记处截断到末尾（这些块总在自然语言之后）。
function stripBlocks(text) {
  const idx = text.search(/===\s*(SETTING|PROMPT_CN)\s*===/)
  const cut = idx >= 0 ? text.slice(0, idx) : text
  return cut.trim()
}
function renderText(t) { return marked.parse(t || '') }
function renderBubble(m) {
  if (m.role === 'user') return escapeHtml(m.content)
  return renderText(stripBlocks(m.content))
}
function escapeHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br/>')
}

function nowTime() {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// 从 AI 完整回复里解析结构化设定与中文 prompt，更新右侧，并记录变更
function parseBlocks(text) {
  const settingM = text.match(/===SETTING===([\s\S]*?)===PROMPT_CN===/)
  const promptM = text.match(/===PROMPT_CN===([\s\S]*?)(===END===|$)/)
  if (!settingM && !promptM) return

  const changes = []
  if (settingM) {
    const obj = {}
    for (const line of settingM[1].trim().split('\n')) {
      const idx = line.indexOf(':')
      const idx2 = line.indexOf('：')
      const p = idx >= 0 && (idx2 < 0 || idx < idx2) ? idx : idx2
      if (p > 0) {
        const key = line.slice(0, p).trim()
        const val = line.slice(p + 1).trim()
        if (key) obj[key] = val
      }
    }
    if (Object.keys(obj).length) {
      // diff 出变化的字段
      const prev = setting.value || {}
      for (const [k, v] of Object.entries(obj)) {
        if (!v || v === '（未设定）') continue
        const old = prev[k]
        if (!old && !prev[k]) {
          if (setting.value) changes.push({ field: k, from: '', to: truncate(v) })  // 新增字段
        } else if (old && old !== v) {
          changes.push({ field: k, from: truncate(old), to: truncate(v) })
        }
      }
      setting.value = obj
    }
  }
  if (promptM) {
    const cn = promptM[1].trim()
    if (cn && cn !== promptCn.value) {
      if (promptCn.value) changes.push({ field: '提示词', from: '', to: '已更新' })
      promptCn.value = cn
      promptEn.value = ''  // prompt 变了，清空旧英文
    }
  }
  // 只有在“已有设定基础上再变化”时才记一条时间线（首次生成不算调整）
  if (changes.length) {
    adjustRound += 1
    changeLog.value.push({ round: adjustRound, time: nowTime(), changes })
  }
}

function truncate(s, n = 16) {
  s = String(s || '')
  return s.length > n ? s.slice(0, n) + '…' : s
}

async function scrollToBottom() {
  await nextTick()
  const el = chatScroll.value
  if (el) el.scrollTop = el.scrollHeight
}

async function send() {
  const text = draft.value.trim()
  if (!text || chatLoading.value) return
  messages.value.push({ role: 'user', content: text })
  draft.value = ''
  const triggerImage = CONFIRM_RE.test(text) && promptCn.value
  const alreadyHasImage = images.value.length > 0
  await scrollToBottom()
  await runChat()
  // 命中确认关键词且已有 prompt → 自动出图；已有图默认走图生图迭代，否则文生图
  if (triggerImage && promptCn.value) generateImage(alreadyHasImage ? 'edit' : 'text')
}

async function runChat() {
  chatLoading.value = true
  streamingText.value = ''
  const history = messages.value.map(m => ({ role: m.role, content: m.content }))
  await ipDesignChatStream(history, {
    onDelta(c) { streamingText.value += c; scrollToBottom() },
    onFinal(payload) {
      const full = payload.raw || streamingText.value
      messages.value.push({ role: 'assistant', content: full })
      parseBlocks(full)
      streamingText.value = ''
    },
    onDone() { chatLoading.value = false; scrollToBottom() },
    onError(err) {
      chatLoading.value = false
      streamingText.value = ''
      messages.value.push({ role: 'assistant', content: '（生成失败：' + (err.message || '请重试') + '）' })
    },
  })
}

const IMG_TIMEOUT_MS = 90000  // 出图超时；模型卡住时避免一直转圈无法重试
let imgReqId = 0              // 标记当前请求，超时/重试后丢弃过期响应

async function generateImage(mode) {
  if (!promptCn.value.trim()) { ElMessage.warning('还没有可用的画面提示词'); return }
  if (mode === 'edit' && !images.value.length) { ElMessage.warning('还没有可修改的图片'); return }
  const reqId = ++imgReqId
  imgLoading.value = true
  imgMode.value = mode
  imgError.value = ''
  try {
    const payload = {
      model: imgModel.value,
      prompt_cn: promptCn.value,
      mode,
      size: '1024x1024',
      n: 1,
    }
    // 图生图以最新一张图为参考（历史项存的是 .src）
    if (mode === 'edit') payload.ref_image = images.value[images.value.length - 1]?.src || ''
    // 超时保护：模型卡住时不会一直卡在 loading
    const res = await Promise.race([
      ipDesignGenerateImage(payload),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('出图超时，模型可能繁忙，请点击重试')), IMG_TIMEOUT_MS)),
    ])
    if (reqId !== imgReqId) return  // 已被新的请求/重试取代，丢弃本次结果
    promptEn.value = res.prompt_en || ''
    if (res.images?.length) {
      for (const im of res.images) {
        const src = im.data_url || im.url || ''
        if (src) images.value.push({ src, mode, promptCn: promptCn.value, ts: Date.now() + images.value.length })
      }
    } else {
      imgError.value = '未返回图片，请重试或调整提示词'
    }
  } catch (e) {
    if (reqId !== imgReqId) return
    imgError.value = e.message || '出图失败，请点击重试'
  } finally {
    if (reqId === imgReqId) imgLoading.value = false
  }
}

// 重试：用同一模式重新出图（超时/失败/卡住时可用）
function retryImage() {
  generateImage(imgMode.value)
}

async function downloadImg(img, n) {
  const src = img.src
  if (!src) return
  try {
    let href = src, revoke = false
    if (!src.startsWith('data:')) {
      const blob = await (await fetch(src)).blob()
      href = URL.createObjectURL(blob); revoke = true
    }
    const a = document.createElement('a')
    a.href = href; a.download = `ip-design-${n}.png`
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    if (revoke) URL.revokeObjectURL(href)
  } catch { ElMessage.error('下载失败，可右键图片另存为') }
}

function resetChat() {
  messages.value = [{ role: 'assistant', content: OPENING }]
  draft.value = ''
  setting.value = null
  promptCn.value = ''
  promptEn.value = ''
  images.value = []
  changeLog.value = []
  adjustRound = 0
  imgError.value = ''
}
</script>

<style scoped>
.ip-layout { display: flex; align-items: stretch; gap: 0; height: calc(100vh - var(--topbar-height) - 100px); }
.left-panel { flex: 1; min-width: 80px; }
.right-panel { flex: none; min-width: 80px; }
.io-panel { display: flex; flex-direction: column; overflow: hidden; padding: 0; }
.io-panel-header { padding: 12px 20px; border-bottom: 1px solid var(--color-border); font-weight: 500; font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; background: #fafafa; flex-shrink: 0; }
.io-panel-body { flex: 1; overflow-y: auto; padding: 16px 20px; }

/* 可拖动分隔条 */
.gutter { flex: none; width: 14px; cursor: col-resize; display: flex; align-items: center; justify-content: center; }
.gutter-bar { width: 3px; height: 48px; border-radius: 3px; background: var(--color-border); transition: background .15s; }
.gutter:hover .gutter-bar, .gutter.dragging .gutter-bar { background: #7c5cff; }

/* 对话区 */
.chat-scroll { flex: 1; overflow-y: auto; padding: 16px 18px; display: flex; flex-direction: column; gap: 14px; }
.msg { display: flex; gap: 10px; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar { flex: none; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #fff; }
.msg.assistant .msg-avatar { background: #7c5cff; }
.msg.user .msg-avatar { background: var(--color-primary); }
.msg-bubble { max-width: 82%; font-size: 14px; line-height: 1.8; color: #2d2d2d; }
/* AI 回复：透明无底色，靠留白和头像区分（ChatGPT 风格） */
.msg.assistant .msg-bubble { background: transparent; padding: 2px 0; max-width: 100%; }
/* 用户消息：保留淡灰气泡 */
.msg.user .msg-bubble { background: #f4f4f5; padding: 10px 14px; border-radius: 16px; }
.msg-bubble :deep(p) { margin: 4px 0; }
.msg-bubble :deep(ul), .msg-bubble :deep(ol) { margin: 4px 0; padding-left: 20px; }
.cursor { align-self: flex-end; color: #7c5cff; animation: blink .8s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }

.chat-input { flex-shrink: 0; border-top: 1px solid var(--color-border); padding: 12px 16px; display: flex; gap: 8px; align-items: flex-end; background: #fff; }
.chat-input .el-textarea { flex: 1; }

/* 右侧结果 */
.rs-block { margin-bottom: 20px; }
.rs-title { font-size: 14px; font-weight: 700; color: #7c5cff; margin-bottom: 10px; }
.setting-row { display: flex; gap: 8px; font-size: 13px; line-height: 1.8; padding: 3px 0; border-bottom: 1px dashed #eee; }
.setting-key { flex: none; width: 48px; color: #999; }
.setting-val { flex: 1; color: #333; }
.prompt-en { margin-top: 8px; font-size: 12px; color: #888; line-height: 1.6; background: #fafafa; padding: 8px 10px; border-radius: 6px; }
.en-label { color: #aaa; }

/* 变更记录时间线 */
.timeline { position: relative; padding-left: 4px; }
.tl-item { display: flex; gap: 10px; padding-bottom: 12px; position: relative; }
.tl-item:not(:last-child)::before { content: ''; position: absolute; left: 4px; top: 14px; bottom: 0; width: 1px; background: #e5e0ff; }
.tl-dot { flex: none; width: 9px; height: 9px; border-radius: 50%; background: #7c5cff; margin-top: 4px; }
.tl-body { flex: 1; }
.tl-head { font-size: 12px; font-weight: 600; color: #555; margin-bottom: 3px; }
.tl-time { color: #bbb; font-weight: 400; margin-left: 6px; }
.tl-change { font-size: 12px; line-height: 1.7; }
.tl-field { color: #7c5cff; margin-right: 4px; }
.tl-from { color: #999; text-decoration: line-through; }
.tl-arrow { color: #bbb; margin: 0 3px; }
.tl-to { color: #333; }

.img-controls { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.ctrl-label { font-size: 13px; color: var(--color-text-secondary); }
.img-btns { display: flex; flex-wrap: wrap; gap: 8px; }
.img-loading { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 24px 0; justify-content: center; color: #999; font-size: 13px; background: #faf9ff; border-radius: 8px; margin-bottom: 12px; }

/* 图片历史画廊 */
.gallery { display: flex; flex-direction: column; gap: 14px; }
.gallery-item { border: 1px solid var(--color-border); border-radius: 10px; padding: 10px; background: #fff; }
.ip-img { width: 100%; border-radius: 8px; background: #fafafa; display: block; }
.ip-img :deep(.el-image__inner) { width: 100%; height: auto; }
.gallery-meta { display: flex; align-items: center; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
.latest-tag { font-size: 11px; color: #e6a23c; }

.wip-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; height: 100%; color: var(--color-text-secondary); text-align: center; }
.wip-placeholder .el-icon { font-size: 36px; opacity: 0.5; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .ip-layout { flex-direction: column; height: auto; } .gutter { display: none; } .right-panel { width: auto !important; } }
</style>
