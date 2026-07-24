<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">抖音爆款脚本</div>
      <div class="page-desc">DeepSeek 流式生成主题标语、内容大纲、分镜头脚本、视频简介，可直接编辑</div>
    </div>
    <div class="promo-layout">
      <!-- 左：输入 -->
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入信息</div>
        <div class="io-panel-body">
          <el-form :model="form" label-position="top">
            <el-form-item label="视频主题" required>
              <el-input v-model="form.subject" placeholder="例：西湖夜游体验vlog" />
            </el-form-item>

            <el-form-item label="视频时长（秒）">
              <el-input-number v-model="form.duration" :min="5" :max="600" :step="5" style="width:100%" />
              <div class="field-hint">默认 30 秒，可自由调整；镜头数量会随时长自动变化</div>
            </el-form-item>

            <el-form-item label="视频风格（可选）">
              <el-input v-model="form.style" placeholder="例：搞笑反差 / 情绪共鸣 / 干货攻略（留空则 AI 自行判断）" clearable />
            </el-form-item>

            <el-button type="primary" :loading="loading" @click="generate" style="width:100%"
              :disabled="!form.subject">
              <el-icon><MagicStick /></el-icon>{{ loading ? '生成中...' : '生成脚本' }}
            </el-button>
          </el-form>
        </div>
      </div>

      <!-- 右：输出 -->
      <div class="io-panel work-card">
        <div class="io-panel-header">
          <el-icon><VideoPlay /></el-icon>抖音脚本
          <div style="flex:1" />
          <template v-if="hasContent">
            <span v-if="!loading" class="editable-tip"><el-icon><EditPen /></el-icon>内容可直接点击编辑</span>
            <el-button link size="small" @click="copyText">
              <el-icon><CopyDocument /></el-icon>复制脚本
            </el-button>
          </template>
        </div>
        <div class="io-panel-body" ref="previewRoot">
          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" style="margin-bottom:12px" />

          <div v-if="!hasContent && !loading" class="wip-placeholder">
            <el-icon><VideoPlay /></el-icon><span>填写信息后生成脚本</span>
          </div>
          <div v-else-if="loading && !raw" class="wip-placeholder">
            <el-icon class="spin"><Loading /></el-icon><span>正在生成...</span>
          </div>

          <div v-else class="dy-preview">
            <!-- 主题标语 -->
            <section v-if="sections.slogans.length || loading" class="dy-block">
              <div class="dy-block-title">🎯 主题标语</div>
              <div v-for="(s, i) in sections.slogans" :key="'s'+i"
                class="dy-slogan" contenteditable="true">{{ s }}</div>
            </section>

            <!-- 内容大纲 -->
            <section v-if="sections.outline.length" class="dy-block">
              <div class="dy-block-title">📋 内容大纲</div>
              <ul class="dy-outline">
                <li v-for="(o, i) in sections.outline" :key="'o'+i" contenteditable="true">{{ o }}</li>
              </ul>
            </section>

            <!-- 分镜头脚本 -->
            <section v-if="sections.shots.length" class="dy-block">
              <div class="dy-block-title">🎬 分镜头脚本</div>
              <div v-for="(shot, i) in sections.shots" :key="'shot'+i" class="shot-card">
                <div class="shot-head">
                  <span class="shot-no">镜头 {{ shot.no }}</span>
                  <span class="shot-meta" contenteditable="true">{{ shot.duration }}</span>
                  <span class="shot-dot">·</span>
                  <span class="shot-meta" contenteditable="true">{{ shot.shotType }}</span>
                </div>
                <div class="shot-row"><span class="shot-label">画面</span>
                  <span class="shot-val" contenteditable="true">{{ shot.visual }}</span></div>
                <div class="shot-row"><span class="shot-label">口播</span>
                  <span class="shot-val" contenteditable="true">{{ shot.voice }}</span></div>
              </div>
            </section>

            <!-- 视频简介 -->
            <section v-if="sections.intro" class="dy-block">
              <div class="dy-block-title">📝 视频简介</div>
              <div class="dy-intro" contenteditable="true">{{ sections.intro }}</div>
            </section>

            <span v-if="loading" class="streaming-cursor">▋</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { generateDouyinStream } from '@/api/promotion.js'

defineOptions({ name: 'DouyinPage' })

const form = ref({ subject: '', duration: 30, style: '' })
const loading = ref(false)
const error = ref('')
const raw = ref('')            // 流式累积的原始文本
const previewRoot = ref(null)

const hasContent = computed(() => raw.value.trim().length > 0)

// 按 ===标语===/===大纲===/===分镜===/===简介=== 解析成结构化四板块
const sections = computed(() => {
  const text = raw.value
  const grab = (tag) => {
    const re = new RegExp(`===\\s*${tag}\\s*===([\\s\\S]*?)(?:===|$)`)
    const m = text.match(re)
    return m ? m[1].trim() : ''
  }
  const slogansRaw = grab('标语')
  const outlineRaw = grab('大纲')
  const shotsRaw = grab('分镜')
  const introRaw = grab('简介')

  const slogans = slogansRaw.split('\n')
    .map(l => l.replace(/^\s*\d+[.、)]\s*/, '').trim())
    .filter(Boolean)

  const outline = outlineRaw.split('\n')
    .map(l => l.replace(/^\s*[-•\d.、)]+\s*/, '').trim())
    .filter(Boolean)

  // 分镜：每行 序号 | 时长 | 景别/运镜 | 画面 | 口播
  const shots = []
  for (const line of shotsRaw.split('\n')) {
    if (line.split('|').length < 5) continue
    const parts = line.split('|').map(p => p.trim())
    // 跳过可能的表头行
    if (/^镜头\s*序号|^序号$/.test(parts[0])) continue
    shots.push({
      no: parts[0].replace(/[^\d]/g, '') || (shots.length + 1),
      duration: parts[1],
      shotType: parts[2],
      visual: parts[3],
      voice: parts[4],
    })
  }

  return { slogans, outline, shots, intro: introRaw }
})

async function generate() {
  if (!form.value.subject.trim()) { ElMessage.warning('请输入视频主题'); return }
  loading.value = true
  error.value = ''
  raw.value = ''
  await generateDouyinStream(
    {
      subject: form.value.subject,
      duration: form.value.duration,
      style: form.value.style,
    },
    {
      onDelta(content) { raw.value += content },
      onFinal(payload) { if (payload.raw) raw.value = payload.raw },
      onDone() { loading.value = false },
      onError(err) {
        error.value = err.message || '脚本生成失败，请稍后重试'
        loading.value = false
      },
    },
  )
}

// 复制：从渲染后的 DOM 读取纯文字（含用户就地编辑），拼成顺畅脚本
function copyText() {
  const root = previewRoot.value
  if (!root) return
  const parts = []
  root.querySelectorAll('.dy-block').forEach(block => {
    const title = block.querySelector('.dy-block-title')?.innerText.trim()
    if (title) parts.push(title.replace(/^[^一-龥A-Za-z]+/, ''))
    // 标语
    block.querySelectorAll('.dy-slogan').forEach(el => {
      const t = el.innerText.trim(); if (t) parts.push('· ' + t)
    })
    // 大纲
    block.querySelectorAll('.dy-outline li').forEach(el => {
      const t = el.innerText.trim(); if (t) parts.push('· ' + t)
    })
    // 分镜卡片
    block.querySelectorAll('.shot-card').forEach(card => {
      const no = card.querySelector('.shot-no')?.innerText.trim()
      const metas = [...card.querySelectorAll('.shot-meta')].map(e => e.innerText.trim()).filter(Boolean)
      const vals = [...card.querySelectorAll('.shot-val')].map(e => e.innerText.trim())
      parts.push(`${no}（${metas.join(' · ')}）`)
      if (vals[0]) parts.push(`  画面：${vals[0]}`)
      if (vals[1]) parts.push(`  口播：${vals[1]}`)
    })
    // 简介
    const intro = block.querySelector('.dy-intro')?.innerText.trim()
    if (intro) parts.push(intro)
    parts.push('')  // 板块间空行
  })
  const text = parts.join('\n').trim()
  if (!text) { ElMessage.warning('暂无可复制的内容'); return }
  navigator.clipboard.writeText(text)
  ElMessage.success('脚本已复制为纯文字')
}
</script>

<style scoped>
.promo-layout { display: grid; grid-template-columns: 380px 1fr; gap: 16px; min-height: 500px; }
.io-panel { display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.io-panel-header { padding: 12px 20px; border-bottom: 1px solid var(--color-border); font-weight: 500; font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; background: #fafafa; flex-shrink: 0; }
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }
.field-hint { font-size: 12px; color: #999; margin-top: 4px; line-height: 1.5; }
.editable-tip { display: inline-flex; align-items: center; gap: 3px; font-size: 12px; color: #999; margin-right: 4px; }

.dy-preview { color: #222; }
.dy-block { margin-bottom: 22px; }
.dy-block-title { font-size: 15px; font-weight: 700; color: #fe2c55; margin-bottom: 10px; }

/* 可编辑通用：悬停浅底、聚焦高亮 */
[contenteditable="true"] { border-radius: 6px; transition: background .15s, box-shadow .15s; cursor: text; outline: none; }
[contenteditable="true"]:hover { background: #fafafa; }
[contenteditable="true"]:focus { background: #fff; box-shadow: 0 0 0 2px rgba(254,44,85,.25); }

.dy-slogan { font-size: 14px; font-weight: 600; padding: 6px 8px; margin-bottom: 6px; background: #fff3f5; border-radius: 8px; }
.dy-outline { padding-left: 20px; margin: 0; }
.dy-outline li { font-size: 14px; line-height: 1.9; padding: 2px 6px; }

.shot-card { border: 1px solid var(--color-border); border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; background: #fff; border-left: 3px solid #fe2c55; }
.shot-head { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }
.shot-no { font-weight: 700; font-size: 14px; color: #fe2c55; }
.shot-meta { font-size: 12px; color: #666; background: #f5f5f5; padding: 1px 8px; border-radius: 10px; }
.shot-dot { color: #ccc; }
.shot-row { display: flex; gap: 8px; font-size: 13px; line-height: 1.7; margin-top: 3px; }
.shot-label { flex: none; width: 32px; color: #999; }
.shot-val { flex: 1; color: #222; }

.dy-intro { font-size: 14px; line-height: 1.9; white-space: pre-wrap; padding: 8px; background: #f7f8fa; border-radius: 8px; }

.streaming-cursor { display: inline-block; animation: blink 0.8s step-end infinite; color: #fe2c55; font-weight: 700; }
@keyframes blink { 50% { opacity: 0; } }

.wip-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; height: 300px; color: var(--color-text-secondary); }
.wip-placeholder .el-icon { font-size: 36px; opacity: 0.5; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .promo-layout { grid-template-columns: 1fr; } }
</style>
