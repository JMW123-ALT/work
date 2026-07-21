<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">图片方案生成</div>
      <div class="page-desc">提示词生成、文生图、图生图三种模式</div>
    </div>

    <el-tabs v-model="activeTab" class="image-tabs">

      <!-- Tab 1: 提示词生成 -->
      <el-tab-pane label="提示词生成" name="prompt">
        <div class="io-layout">
          <div class="io-panel work-card">
            <div class="io-panel-header">
              <el-icon><EditPen /></el-icon>输入主题
            </div>
            <div class="io-panel-body">
              <el-form label-position="top">
                <el-form-item label="画面主题 *">
                  <el-input
                    v-model="promptForm.theme"
                    placeholder="例：黄山云海日出，意境空灵"
                  />
                </el-form-item>
                <el-form-item label="风格">
                  <el-radio-group v-model="promptForm.style" @change="onStyleChange">
                    <el-radio-button label="写实摄影" />
                    <el-radio-button label="国风插画" />
                    <el-radio-button label="水墨" />
                    <el-radio-button label="3D渲染" />
                    <el-radio-button label="其他" />
                  </el-radio-group>
                  <el-input
                    v-if="promptForm.style === '其他'"
                    v-model="promptForm.customStyle"
                    placeholder="请输入自定义风格，如：赛博朋克、油画、像素风..."
                    style="margin-top:8px"
                    clearable
                  />
                </el-form-item>
                <el-form-item label="比例">
                  <el-radio-group v-model="promptForm.ratio">
                    <el-radio-button label="16:9" />
                    <el-radio-button label="1:1" />
                    <el-radio-button label="9:16" />
                    <el-radio-button label="4:3" />
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="补充说明（可选）">
                  <el-input v-model="promptForm.extra" placeholder="其它要求，如特定构图、色调..." />
                </el-form-item>
                <el-button type="primary" :loading="promptLoading" @click="genPrompt" style="width:100%">
                  生成提示词
                </el-button>
              </el-form>
            </div>
          </div>
          <div class="io-panel work-card">
            <div class="io-panel-header">
              <el-icon><Document /></el-icon>生成的提示词
            </div>
            <div class="io-panel-body">
              <el-alert v-if="promptError" :title="promptError" type="error" show-icon :closable="false" style="margin-bottom:12px" />
              <div v-if="!promptResult && !promptError" class="wip-placeholder">
                <el-icon><Picture /></el-icon><span>填写主题后生成</span>
              </div>
              <div v-else-if="promptResult">
                <div class="result-field">
                  <div class="result-label">正向提示词（Prompt）</div>
                  <el-input v-model="promptResult.prompt" type="textarea" :autosize="{ minRows: 4 }" readonly />
                </div>
                <div class="result-field">
                  <div class="result-label">负向提示词（Negative Prompt）</div>
                  <el-input v-model="promptResult.negative_prompt" type="textarea" :autosize="{ minRows: 2 }" readonly />
                </div>
                <div class="result-meta">
                  <el-tag>风格：{{ promptResult.style }}</el-tag>
                  <el-tag type="info">比例：{{ promptResult.ratio }}</el-tag>
                  <el-tag type="success">建议模型：{{ promptResult.model_suggestion }}</el-tag>
                </div>
                <div class="result-actions">
                  <el-button plain @click="copyPrompt">
                    <el-icon><CopyDocument /></el-icon>复制提示词
                  </el-button>
                  <el-button type="primary" plain @click="usePromptForT2I">
                    <el-icon><Right /></el-icon>用于文生图
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 文生图 -->
      <el-tab-pane label="文生图" name="text2img">
        <div class="io-layout">
          <div class="io-panel work-card">
            <div class="io-panel-header">
              <el-icon><EditPen /></el-icon>输入提示词
            </div>
            <div class="io-panel-body">
              <el-form label-position="top">
                <el-form-item label="选择模型">
                  <el-select v-model="t2iForm.model" placeholder="选择生图模型" style="width:100%">
                    <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
                  </el-select>
                </el-form-item>
                <el-form-item label="图片提示词（中/英文均可）" required>
                  <el-input v-model="t2iForm.prompt" type="textarea" :autosize="{ minRows: 4 }" placeholder="描述你想要的画面..." />
                </el-form-item>
                <el-form-item label="负面提示词（可选）">
                  <el-input v-model="t2iForm.negative" type="textarea" :autosize="{ minRows: 2 }" placeholder="不希望出现的内容" />
                </el-form-item>
                <div class="param-row">
                  <el-form-item label="图片尺寸" class="param-item">
                    <el-select v-model="t2iForm.size" style="width:100%">
                      <el-option label="1024×1024（1:1）" value="1024x1024" />
                      <el-option label="1536×1024（3:2 横）" value="1536x1024" />
                      <el-option label="1024×1536（2:3 竖）" value="1024x1536" />
                      <el-option label="2048×2048（2K 1:1）" value="2048x2048" />
                      <el-option label="2048×1152（2K 16:9）" value="2048x1152" />
                      <el-option label="3840×2160（4K 横）" value="3840x2160" />
                      <el-option label="2160×3840（4K 竖）" value="2160x3840" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="生成数量" class="param-item">
                    <el-input-number v-model="t2iForm.n" :min="1" :max="4" style="width:100%" />
                  </el-form-item>
                </div>
                <el-form-item label="质量（可选）">
                  <el-radio-group v-model="t2iForm.quality">
                    <el-radio-button label="">默认</el-radio-button>
                    <el-radio-button label="standard">标准</el-radio-button>
                    <el-radio-button label="hd">高清</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-button
                  type="primary"
                  :loading="t2iLoading"
                  :disabled="!t2iForm.prompt.trim() || !t2iForm.model"
                  @click="generateT2I"
                  style="width:100%"
                >生成图片</el-button>
              </el-form>
            </div>
          </div>
          <div class="io-panel work-card">
            <div class="io-panel-header"><el-icon><Picture /></el-icon>图片预览</div>
            <div class="io-panel-body">
              <el-alert v-if="t2iError" :title="t2iError" type="error" show-icon :closable="false" style="margin-bottom:12px" />
              <div v-if="t2iLoading" class="wip-placeholder">
                <el-icon class="spin"><Loading /></el-icon><span>正在生成图片，请稍候...</span>
              </div>
              <div v-else-if="t2iImages.length === 0 && !t2iError" class="wip-placeholder">
                <el-icon><Picture /></el-icon><span>输入提示词后生成</span>
              </div>
              <div v-else class="image-grid">
                <div v-for="(img, idx) in t2iImages" :key="idx" class="image-cell">
                  <el-image
                    :src="imgSrc(img)"
                    fit="contain"
                    class="grid-image"
                    :preview-src-list="t2iImages.map(imgSrc)"
                    :initial-index="idx"
                  />
                  <el-button size="small" plain @click="downloadImage(img, `t2i-${idx}`)">
                    <el-icon><Download /></el-icon>下载
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 图生图 -->
      <el-tab-pane label="图生图" name="img2img">
        <div class="io-layout">
          <div class="io-panel work-card">
            <div class="io-panel-header"><el-icon><EditPen /></el-icon>参考图 + 提示词</div>
            <div class="io-panel-body">
              <el-form label-position="top">
                <el-form-item label="选择模型">
                  <el-select v-model="i2iForm.model" placeholder="选择生图模型" style="width:100%">
                    <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
                  </el-select>
                </el-form-item>
                <el-form-item label="上传参考图">
                  <el-upload drag accept="image/jpeg,image/png,image/webp" :auto-upload="false"
                    v-model:file-list="i2iFiles" :limit="1">
                    <el-icon><UploadFilled /></el-icon>
                    <div>拖拽或点击上传参考图（jpg/png/webp，最大 10MB）</div>
                  </el-upload>
                </el-form-item>
                <el-form-item label="修改描述">
                  <el-input v-model="i2iForm.prompt" type="textarea" :autosize="{ minRows: 3 }" placeholder="描述对图片的修改要求..." />
                </el-form-item>
                <el-form-item label="负面提示词（可选）">
                  <el-input v-model="i2iForm.negative" type="textarea" :autosize="{ minRows: 2 }" placeholder="不希望出现的内容" />
                </el-form-item>
                <el-form-item label="参考强度">
                  <el-slider v-model="i2iForm.strength" :min="0" :max="1" :step="0.05" show-input />
                </el-form-item>
                <el-button type="primary" :loading="i2iLoading"
                  :disabled="i2iFiles.length === 0 || !i2iForm.model"
                  @click="generateI2I" style="width:100%">
                  生成图片
                </el-button>
              </el-form>
            </div>
          </div>
          <div class="io-panel work-card">
            <div class="io-panel-header"><el-icon><Picture /></el-icon>生成结果</div>
            <div class="io-panel-body">
              <el-alert v-if="i2iError" :title="i2iError" type="warning" show-icon :closable="false" style="margin-bottom:12px" />
              <div v-if="i2iLoading" class="wip-placeholder">
                <el-icon class="spin"><Loading /></el-icon><span>正在生成图片，请稍候...</span>
              </div>
              <div v-else-if="i2iImages.length === 0 && !i2iError" class="wip-placeholder">
                <el-icon><Picture /></el-icon><span>上传参考图并填写提示词后生成</span>
              </div>
              <div v-else class="image-grid">
                <div v-for="(img, idx) in i2iImages" :key="idx" class="image-cell">
                  <el-image
                    :src="imgSrc(img)"
                    fit="contain"
                    class="grid-image"
                    :preview-src-list="i2iImages.map(imgSrc)"
                    :initial-index="idx"
                  />
                  <el-button size="small" plain @click="downloadImage(img, `i2i-${idx}`)">
                    <el-icon><Download /></el-icon>下载
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

    </el-tabs>

    <!-- 生成历史 / 素材库 -->
    <div v-if="history.length" class="work-card history-card">
      <div class="history-header">
        <span><el-icon><PictureFilled /></el-icon> 本次生成记录（{{ history.length }}）</span>
        <el-button size="small" text @click="history = []">清空</el-button>
      </div>
      <div class="history-grid">
        <div v-for="(img, idx) in history" :key="idx" class="history-item">
          <el-image :src="imgSrc(img)" fit="cover" class="history-thumb"
            :preview-src-list="history.map(imgSrc)" :initial-index="idx" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// keep-alive 通过组件名缓存，必须显式注册
defineOptions({ name: 'ImagePlanPage' })
import { ElMessage } from 'element-plus'
import {
  listImageModels,
  generateImagePrompt,
  generateTextToImage,
  generateImageToImage,
} from '@/api/planning.js'

const activeTab = ref('prompt')

// ── 模型列表（带兜底，加载失败不白屏） ─────────────────────────────────────
const FALLBACK_MODELS = [
  'gpt-image-2',
  'gpt-image-2-pro',
]
const availableModels = ref([...FALLBACK_MODELS])
const defaultModel = ref('gpt-image-2')

// ── 生成历史（本次会话内，最新在前） ───────────────────────────────────────
const history = ref([])
function pushHistory(images) {
  if (images?.length) history.value.unshift(...images)
}

function imgSrc(img) {
  return img.data_url || img.url || ''
}

onMounted(async () => {
  try {
    const res = await listImageModels()
    if (res.models?.length) availableModels.value = res.models
    if (res.default) defaultModel.value = res.default
  } catch {
    // 使用兜底列表，不做任何提示
  }
  t2iForm.value.model = defaultModel.value
  i2iForm.value.model = defaultModel.value
})

// ── 提示词生成 Tab ──────────────────────────────────────────────────────────
const promptLoading = ref(false)
const promptError = ref('')
const promptResult = ref(null)
const promptForm = ref({ theme: '', style: '写实摄影', ratio: '16:9', extra: '', customStyle: '' })

// 切换到"其他"时聚焦自定义输入框
function onStyleChange(val) {
  if (val !== '其他') promptForm.value.customStyle = ''
}

// 取最终生效的风格值
function resolvedStyle() {
  return promptForm.value.style === '其他'
    ? (promptForm.value.customStyle.trim() || '其他')
    : promptForm.value.style
}

async function genPrompt() {
  if (!promptForm.value.theme.trim()) { ElMessage.warning('请输入画面主题'); return }
  if (promptForm.value.style === '其他' && !promptForm.value.customStyle.trim()) {
    ElMessage.warning('请填写自定义风格'); return
  }
  promptLoading.value = true
  promptError.value = ''
  promptResult.value = null
  try {
    promptResult.value = await generateImagePrompt({
      theme: promptForm.value.theme,
      style: resolvedStyle(),
      ratio: promptForm.value.ratio,
      extra: promptForm.value.extra,
    })
  } catch (e) {
    promptError.value = e.message || '提示词生成失败，请稍后重试'
  } finally {
    promptLoading.value = false
  }
}
function copyPrompt() {
  if (!promptResult.value) return
  navigator.clipboard.writeText(promptResult.value.prompt)
  ElMessage.success('已复制到剪贴板')
}

function usePromptForT2I() {
  if (!promptResult.value) return
  t2iForm.value.prompt = promptResult.value.prompt
  t2iForm.value.negative = promptResult.value.negative_prompt
  const suggested = promptResult.value.model_suggestion
  if (suggested && availableModels.value.includes(suggested)) {
    t2iForm.value.model = suggested
  }
  activeTab.value = 'text2img'
  ElMessage.success('提示词已填入文生图')
}

// ── 文生图 Tab ──────────────────────────────────────────────────────────────
const t2iLoading = ref(false)
const t2iError = ref('')
const t2iImages = ref([])
const t2iForm = ref({ model: '', prompt: '', negative: '', size: '1024x1024', n: 1, quality: '' })

async function generateT2I() {
  if (!t2iForm.value.prompt.trim()) { ElMessage.warning('请输入提示词'); return }
  t2iLoading.value = true
  t2iError.value = ''
  t2iImages.value = []
  try {
    const res = await generateTextToImage({
      model: t2iForm.value.model,
      prompt: t2iForm.value.prompt,
      negative_prompt: t2iForm.value.negative,
      size: t2iForm.value.size,
      n: t2iForm.value.n,
      quality: t2iForm.value.quality,
    })
    t2iImages.value = res.images || []
    if (t2iImages.value.length === 0) t2iError.value = '未返回图片，请更换提示词后重试'
    pushHistory(t2iImages.value)
  } catch (e) {
    t2iError.value = e.message || '图片生成失败，请稍后重试'
  } finally {
    t2iLoading.value = false
  }
}

// ── 图生图 Tab ──────────────────────────────────────────────────────────────
const i2iLoading = ref(false)
const i2iError = ref('')
const i2iImages = ref([])
const i2iFiles = ref([])
const i2iForm = ref({ model: '', prompt: '', negative: '', strength: 0.75 })

async function generateI2I() {
  if (i2iFiles.value.length === 0) { ElMessage.warning('请先上传参考图'); return }
  i2iLoading.value = true
  i2iError.value = ''
  i2iImages.value = []
  try {
    const file = i2iFiles.value[0].raw
    const fd = new FormData()
    fd.append('image', file)
    fd.append('model', i2iForm.value.model)
    fd.append('prompt', i2iForm.value.prompt)
    fd.append('negative_prompt', i2iForm.value.negative)
    fd.append('strength', String(i2iForm.value.strength))
    fd.append('size', '1024x1024')
    const res = await generateImageToImage(fd)
    i2iImages.value = res.images || []
    pushHistory(i2iImages.value)
  } catch (e) {
    const msg = e.message || ''
    if (msg.includes('not supported') || msg.includes('501')) {
      i2iError.value = '当前接口暂未确认支持图生图，请等待后续更新'
    } else {
      i2iError.value = msg || '图生图失败，请稍后重试'
    }
  } finally {
    i2iLoading.value = false
  }
}

// ── 下载 ─────────────────────────────────────────────────────────────────────
async function downloadImage(img, name) {
  const src = imgSrc(img)
  if (!src) return
  try {
    let href = src
    let revoke = false
    if (!src.startsWith('data:')) {
      const resp = await fetch(src)
      const blob = await resp.blob()
      href = URL.createObjectURL(blob)
      revoke = true
    }
    const a = document.createElement('a')
    a.href = href
    a.download = `${name}-${Date.now()}.png`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    if (revoke) URL.revokeObjectURL(href)
  } catch {
    ElMessage.error('下载失败，可右键图片另存为')
  }
}
</script>

<style scoped>
.image-tabs { margin-top: -8px; }
.io-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
  min-height: 400px;
}
.io-panel { display: flex; flex-direction: column; overflow: hidden; padding: 0; }
.io-panel-header {
  padding: 12px 20px;
  border-bottom: 1px solid var(--color-border);
  font-weight: 500;
  font-size: 13px;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fafafa;
  flex-shrink: 0;
}
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }
.param-row { display: flex; gap: 12px; }
.param-item { flex: 1; }
.result-field { margin-bottom: 12px; }
.result-label { font-size: 12px; color: #888; margin-bottom: 4px; }
.result-meta { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }
.result-actions { display: flex; gap: 8px; margin-top: 8px; }
.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}
.image-cell { display: flex; flex-direction: column; gap: 6px; align-items: center; }
.grid-image {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: #fafafa;
}
.history-card { margin-top: 16px; padding: 16px 20px; }
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}
.history-header span { display: flex; align-items: center; gap: 6px; }
.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  gap: 10px;
}
.history-thumb {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  cursor: pointer;
}
.wip-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 200px;
  color: var(--color-text-secondary);
}
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .io-layout { grid-template-columns: 1fr; } }
</style>
