<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">小红书爆款文案</div>
      <div class="page-desc">DeepSeek 联网参考最新爆款，一键生成文案 + 配图，排版好可直接发布</div>
    </div>
    <div class="promo-layout">
      <!-- 左：输入 -->
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入信息</div>
        <div class="io-panel-body">
          <el-form :model="form" label-position="top">
            <el-form-item label="活动/景区/产品名称" required>
              <el-input v-model="form.subject" placeholder="例：黄山景区秋叶季" />
            </el-form-item>
            <el-form-item label="核心亮点（2-4 条）">
              <el-input v-model="form.highlights" type="textarea" :autosize="{ minRows: 3 }"
                placeholder="一行一条，例：&#10;云海日出拍出大片&#10;万亩秋叶绝美" />
            </el-form-item>

            <el-form-item label="目标人群">
              <el-checkbox-group v-model="form.audience">
                <el-checkbox label="学生党" /><el-checkbox label="情侣" />
                <el-checkbox label="家庭亲子" /><el-checkbox label="摄影爱好者" />
                <el-checkbox label="其他" />
              </el-checkbox-group>
              <el-input v-if="form.audience.includes('其他')" v-model="form.audienceCustom"
                placeholder="自定义人群，如：银发族、独自旅行、宝妈..." style="margin-top:8px" clearable />
            </el-form-item>

            <el-form-item label="语气风格">
              <el-radio-group v-model="form.tone" @change="onToneChange">
                <el-radio-button label="活泼种草" /><el-radio-button label="文艺小清新" />
                <el-radio-button label="攻略干货" /><el-radio-button label="其他" />
              </el-radio-group>
              <el-input v-if="form.tone === '其他'" v-model="form.toneCustom"
                placeholder="自定义语气，如：搞笑幽默、高级感、亲切唠嗑..." style="margin-top:8px" clearable />
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="form.useWebSearch">联网参考最新爆款风格</el-checkbox>
            </el-form-item>

            <el-button type="primary" :loading="loading" @click="generate" style="width:100%"
              :disabled="!form.subject">
              <el-icon><MagicStick /></el-icon>生成文案
            </el-button>
          </el-form>
        </div>
      </div>

      <!-- 右：输出 -->
      <div class="io-panel work-card">
        <div class="io-panel-header">
          <el-icon><Document /></el-icon>小红书文案 + 配图
          <div style="flex:1" />
          <el-button v-if="result" link size="small" @click="copyAll">
            <el-icon><CopyDocument /></el-icon>复制全文
          </el-button>
        </div>
        <div class="io-panel-body">
          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" style="margin-bottom:12px" />

          <div v-if="!result && !loading && !streamingText" class="wip-placeholder">
            <el-icon><StarFilled /></el-icon><span>填写信息后生成文案</span>
          </div>
          <div v-else-if="!result && !streamingText && loading" class="wip-placeholder">
            <el-icon class="spin"><Loading /></el-icon><span>联网检索中...</span>
          </div>
          <div v-else-if="!result && streamingText" class="result-preview">
            <div class="xhs-preview">
              <div class="streaming-text">{{ streamingText }}<span v-if="loading" class="streaming-cursor">▋</span></div>
            </div>
          </div>

          <div v-else class="result-preview">
            <!-- 排版好的小红书预览卡片（可直接编辑） -->
            <div class="xhs-preview">
              <!-- 配图区（在文案上方，模拟小红书图文帖） -->
              <div v-if="images.length" class="xhs-images" :class="{ single: images.length === 1 }">
                <el-image v-for="(img, i) in images" :key="i" :src="imgSrc(img)" fit="cover"
                  class="xhs-img" :preview-src-list="images.map(imgSrc)" :initial-index="i" />
              </div>
              <div class="edit-hint"><el-icon><EditPen /></el-icon>内容可直接编辑</div>
              <el-input v-model="draft.title" type="textarea" :autosize="{ minRows: 1 }"
                class="xhs-edit edit-title" placeholder="标题" />
              <el-input v-model="draft.body" type="textarea" :autosize="{ minRows: 4 }"
                class="xhs-edit edit-body" placeholder="正文" />
              <el-input v-model="draft.tagsText" type="textarea" :autosize="{ minRows: 1 }"
                class="xhs-edit edit-tags" placeholder="#标签1 #标签2 #标签3" />
            </div>

            <!-- 联网参考来源 -->
            <div v-if="result.references && result.references.length" class="refs">
              <div class="refs-title">📎 联网参考的爆款标题</div>
              <div v-for="(r, i) in result.references" :key="i" class="ref-item">· {{ r }}</div>
            </div>

            <!-- 配图提示词（可选，叠加在自动提示词之后） -->
            <div class="img-prompt-row">
              <span class="ctrl-label">配图提示词（可选）</span>
              <el-input v-model="imgPrompt" type="textarea" :autosize="{ minRows: 2 }"
                placeholder="补充你想要的画面，如：清晨柔光、航拍视角、暖色调、有人物入镜...（留空则用文案自动生成）" />
            </div>

            <!-- 配图控制 -->
            <div class="img-controls">
              <span class="ctrl-label">配图</span>
              <el-select v-model="imgModel" size="small" style="width:150px">
                <el-option v-for="m in models" :key="m" :label="m" :value="m" />
              </el-select>
              <span class="ctrl-label">数量</span>
              <el-input-number v-model="imgCount" :min="1" :max="4" size="small" style="width:110px" />
              <el-button type="danger" plain size="small" :loading="imgLoading" @click="genImages">
                <el-icon><Picture /></el-icon>生成配图
              </el-button>
              <el-button v-if="images.length" size="small" link @click="downloadAll">
                <el-icon><Download /></el-icon>下载全部
              </el-button>
            </div>
            <el-alert v-if="imgError" :title="imgError" type="warning" show-icon :closable="false" style="margin-top:8px" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  generateXiaohongshuStream,
  generateXiaohongshuImages,
  listImageModels,
} from '@/api/promotion.js'

defineOptions({ name: 'XiaohongshuPage' })

const form = ref({
  subject: '',
  highlights: '',
  audience: ['情侣'],
  audienceCustom: '',
  tone: '活泼种草',
  toneCustom: '',
  useWebSearch: true,
})
const loading = ref(false)
const error = ref('')
const result = ref(null)
const streamingText = ref('')

// 可编辑草稿（生成后填充，用户可直接在预览卡片里修改）
const draft = ref({ title: '', body: '', tagsText: '' })
// 从 tagsText 解析出干净的标签数组（去掉 # 和空白）
const draftTags = computed(() =>
  draft.value.tagsText.split(/[\s#]+/).map(t => t.trim()).filter(Boolean),
)
// 组合成可复制/发布的完整文案（始终反映用户最新编辑）
const composedText = computed(() => {
  const tagLine = draftTags.value.map(t => `#${t}`).join(' ')
  return [draft.value.title, draft.value.body, tagLine]
    .map(s => (s || '').trim()).filter(Boolean).join('\n\n')
})

// ── 配图 ──
const FALLBACK_MODELS = ['gpt-image-2', 'gpt-image-2-pro']
const models = ref([...FALLBACK_MODELS])
const imgModel = ref('gpt-image-2')
const imgCount = ref(2)
const imgLoading = ref(false)
const imgError = ref('')
const images = ref([])
const imgPrompt = ref('')  // 用户补充的配图提示词（可选）

onMounted(async () => {
  try {
    const res = await listImageModels()
    if (res.models?.length) models.value = res.models
    if (res.default) imgModel.value = res.default
  } catch { /* 兜底列表 */ }
})

function onToneChange(val) {
  if (val !== '其他') form.value.toneCustom = ''
}

function resolvedAudience() {
  const list = form.value.audience.filter(a => a !== '其他')
  if (form.value.audience.includes('其他') && form.value.audienceCustom.trim()) {
    list.push(form.value.audienceCustom.trim())
  }
  return list.join('、') || '大众游客'
}
function resolvedTone() {
  return form.value.tone === '其他'
    ? (form.value.toneCustom.trim() || '活泼种草')
    : form.value.tone
}

async function generate() {
  if (!form.value.subject.trim()) { ElMessage.warning('请输入名称'); return }
  if (form.value.tone === '其他' && !form.value.toneCustom.trim()) {
    ElMessage.warning('请填写自定义语气'); return
  }
  loading.value = true
  error.value = ''
  result.value = null
  streamingText.value = ''
  draft.value = { title: '', body: '', tagsText: '' }
  images.value = []
  await generateXiaohongshuStream(
    {
      subject: form.value.subject,
      highlights: form.value.highlights,
      audience: resolvedAudience(),
      tone: resolvedTone(),
      use_web_search: form.value.useWebSearch,
    },
    {
      onDelta(content) { streamingText.value += content },
      onFinal(payload) {
        result.value = payload
        // 填充可编辑草稿
        draft.value = {
          title: payload.title || '',
          body: payload.body || '',
          tagsText: (payload.tags || []).map(t => `#${t}`).join(' '),
        }
      },
      onDone() { loading.value = false },
      onError(err) {
        error.value = err.message || '文案生成失败，请稍后重试'
        loading.value = false
      },
    },
  )
}

function imgSrc(img) {
  return img.data_url || img.url || ''
}

async function genImages() {
  if (!result.value) return
  imgLoading.value = true
  imgError.value = ''
  try {
    // 用（编辑后的）文案标题 + 亮点作为基础提示词，叠加用户补充的提示词
    const extra = imgPrompt.value.trim()
    const prompt = `小红书风格配图，主题：${form.value.subject}。${draft.value.title || result.value.title}。${form.value.highlights}。`
      + (extra ? `${extra}。` : '')
      + '构图精美，色彩明亮，适合社交媒体分享'
    const res = await generateXiaohongshuImages({
      model: imgModel.value,
      prompt,
      negative_prompt: '低质量、模糊、水印、文字',
      size: '1024x1024',
      n: imgCount.value,
    })
    images.value = res.images || []
    if (!images.value.length) imgError.value = '未返回图片，请重试'
  } catch (e) {
    imgError.value = e.message || '配图生成失败'
  } finally {
    imgLoading.value = false
  }
}

function copyAll() {
  if (!result.value) return
  // 复制用户编辑后的最新内容
  navigator.clipboard.writeText(composedText.value || result.value.full_text)
  ElMessage.success('文案已复制，图片请在预览区右键保存或点下载')
}

async function downloadAll() {
  for (let i = 0; i < images.value.length; i++) {
    const src = imgSrc(images.value[i])
    if (!src) continue
    try {
      let href = src, revoke = false
      if (!src.startsWith('data:')) {
        const blob = await (await fetch(src)).blob()
        href = URL.createObjectURL(blob); revoke = true
      }
      const a = document.createElement('a')
      a.href = href
      a.download = `xhs-${form.value.subject || 'image'}-${i + 1}.png`
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      if (revoke) URL.revokeObjectURL(href)
    } catch { /* 单张失败跳过 */ }
  }
}
</script>

<style scoped>
.promo-layout { display: grid; grid-template-columns: 380px 1fr; gap: 16px; min-height: 500px; }
.io-panel { display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.io-panel-header { padding: 12px 20px; border-bottom: 1px solid var(--color-border); font-weight: 500; font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; background: #fafafa; flex-shrink: 0; }
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }

.streaming-text { white-space: pre-wrap; font-size: 14px; color: #333; line-height: 1.9; }
.streaming-cursor { display: inline-block; animation: blink 0.8s step-end infinite; color: #ff2442; }
@keyframes blink { 50% { opacity: 0; } }

.xhs-preview { background: #fff7f7; border: 1px solid #ffd6d6; border-radius: 12px; padding: 20px; }
.xhs-images { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.xhs-images.single { }
.xhs-img { width: 120px; height: 120px; border-radius: 10px; flex: none; }
.xhs-title { font-size: 16px; font-weight: 700; color: #ff2442; margin-bottom: 12px; line-height: 1.5; }
.xhs-body { font-size: 14px; color: #333; line-height: 1.9; white-space: pre-wrap; margin-bottom: 12px; }
.xhs-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.xhs-tag { font-size: 13px; color: #ff2442; }

/* 可编辑文案：输入框融入预览卡片，聚焦时才显边框 */
.edit-hint { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #c0868a; margin-bottom: 8px; }
.xhs-edit { margin-bottom: 10px; }
.xhs-edit :deep(.el-textarea__inner) {
  background: transparent; box-shadow: none; border: 1px solid transparent;
  border-radius: 8px; padding: 4px 8px; resize: none; transition: border-color .15s, background .15s;
}
.xhs-edit :deep(.el-textarea__inner:hover) { border-color: #ffd6d6; }
.xhs-edit :deep(.el-textarea__inner:focus) { border-color: #ff2442; background: #fff; }
.edit-title :deep(.el-textarea__inner) { font-size: 16px; font-weight: 700; color: #ff2442; line-height: 1.5; }
.edit-body :deep(.el-textarea__inner) { font-size: 14px; color: #333; line-height: 1.9; }
.edit-tags :deep(.el-textarea__inner) { font-size: 13px; color: #ff2442; }

.img-prompt-row { margin-top: 14px; display: flex; flex-direction: column; gap: 6px; }

.refs { margin-top: 14px; padding: 12px 14px; background: #f7f8fa; border-radius: 8px; }
.refs-title { font-size: 12px; color: #888; margin-bottom: 6px; }
.ref-item { font-size: 12px; color: #666; line-height: 1.7; }

.img-controls { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 16px; padding-top: 14px; border-top: 1px dashed var(--color-border); }
.ctrl-label { font-size: 13px; color: var(--color-text-secondary); }

.wip-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; height: 300px; color: var(--color-text-secondary); }
.wip-placeholder .el-icon { font-size: 36px; opacity: 0.5; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .promo-layout { grid-template-columns: 1fr; } }
</style>
