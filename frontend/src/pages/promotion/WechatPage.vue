<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">公众号爆款文案</div>
      <div class="page-desc">DeepSeek 流式生成推文，正文自动配图（可上传或 AI 生成），支持在线编辑</div>
    </div>
    <div class="promo-layout">
      <!-- 左：输入 -->
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入信息</div>
        <div class="io-panel-body">
          <el-form :model="form" label-position="top">
            <el-form-item label="文章主题" required>
              <el-input v-model="form.subject" placeholder="例：秋季黄山游全攻略" />
            </el-form-item>

            <el-form-item label="写作风格（可选）">
              <el-input v-model="form.style" placeholder="例：轻松有网感 / 文艺深度 / 专业严谨" clearable />
            </el-form-item>

            <el-form-item label="文章类型（可选）">
              <el-input v-model="form.articleType" placeholder="例：旅游攻略 / 活动推广 / 文化故事 / 行业资讯" clearable />
            </el-form-item>

            <el-form-item label="目标字数（可选）">
              <el-input-number v-model="form.wordCount" :min="300" :max="5000" :step="100" style="width:100%" />
            </el-form-item>

            <el-form-item label="文章大纲（可选）">
              <el-input v-model="form.outline" type="textarea" :autosize="{ minRows: 3, maxRows: 8 }"
                placeholder="一行一个要点，如：&#10;开篇：秋日黄山的魅力&#10;交通与门票&#10;三大必看景点&#10;实用贴士" />
            </el-form-item>

            <el-divider content-position="left">配图</el-divider>

            <el-form-item label="上传配图（可选，将按顺序插入文中）">
              <el-upload drag multiple accept="image/jpeg,image/png,image/webp"
                :auto-upload="false" v-model:file-list="imageFiles" :limit="6" list-type="picture-card">
                <el-icon><Plus /></el-icon>
              </el-upload>
              <div class="field-hint">支持 jpg/png/webp，单张最大 10MB，最多 6 张</div>
            </el-form-item>

            <el-form-item label="搜索图片（可选，从图库挑选后插入文中）">
              <el-button plain @click="openSearch" style="width:100%">
                <el-icon><Search /></el-icon>搜索图库配图
              </el-button>
              <div v-if="pickedStock.length" class="picked-grid">
                <div v-for="(p, i) in pickedStock" :key="p.id ?? i" class="picked-item">
                  <el-image :src="p.thumb" fit="cover" class="picked-thumb" />
                  <el-icon class="picked-remove" @click="removePicked(i)"><CircleClose /></el-icon>
                </div>
              </div>
              <div class="field-hint">已选 {{ pickedStock.length }} 张，将按顺序插入文中</div>
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="form.autoGenerate">用 AI 文生图补足剩余配图位</el-checkbox>
            </el-form-item>
            <el-form-item v-if="form.autoGenerate" label="配图模型">
              <el-select v-model="form.imageModel" size="default" style="width:100%">
                <el-option v-for="m in models" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="form.useWebSearch">联网参考最新爆款风格</el-checkbox>
            </el-form-item>

            <el-button type="primary" :loading="loading" @click="generate" style="width:100%"
              :disabled="!form.subject">
              <el-icon><MagicStick /></el-icon>{{ loading ? '生成中...' : '生成推文' }}
            </el-button>
          </el-form>
        </div>
      </div>

      <!-- 右：输出 -->
      <div class="io-panel work-card">
        <div class="io-panel-header">
          <el-icon><ChatLineRound /></el-icon>公众号推文
          <div style="flex:1" />
          <template v-if="hasContent">
            <span v-if="!loading" class="editable-tip"><el-icon><EditPen /></el-icon>正文可直接点击编辑</span>
            <el-button link size="small" @click="copyText">
              <el-icon><CopyDocument /></el-icon>复制正文
            </el-button>
          </template>
        </div>
        <div class="io-panel-body">
          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" style="margin-bottom:12px" />

          <!-- 空状态 -->
          <div v-if="!hasContent && !loading" class="wip-placeholder">
            <el-icon><ChatLineRound /></el-icon><span>填写信息后生成推文</span>
          </div>
          <!-- 联网检索中（尚无正文） -->
          <div v-else-if="loading && !markdown" class="wip-placeholder">
            <el-icon class="spin"><Loading /></el-icon>
            <span>{{ form.useWebSearch ? '联网检索爆款中...' : '正在生成...' }}</span>
          </div>

          <!-- 所见即所得：渲染 Markdown + 内联图片，正文块生成完成后可直接点击编辑 -->
          <div v-else class="wechat-preview" ref="previewRoot">
            <template v-for="(seg, i) in renderedSegments" :key="i">
              <div v-if="seg.type === 'html'" class="md-output" :class="{ editable: !loading }"
                :contenteditable="!loading" v-html="seg.html" />
              <div v-else class="article-image" contenteditable="false">
                <!-- 已删除：显示可撤销/替换的占位条 -->
                <div v-if="images[seg.index]?.deleted" class="image-removed">
                  <el-icon><Picture /></el-icon>配图已移除
                  <span class="link" @click="restoreImage(seg.index)">撤销</span>
                  <span class="sep">·</span>
                  <span class="link" @click="replaceViaSearch(seg.index)">换一张</span>
                </div>
                <template v-else>
                  <div v-if="imgSrcFor(seg.index)" class="img-wrap"
                    :style="{ width: (images[seg.index]?.width || 100) + '%' }">
                    <el-image :src="imgSrcFor(seg.index)" fit="contain"
                      :preview-src-list="allImageSrcs" :initial-index="previewIndexFor(seg.index)" class="wx-img" />
                    <div v-if="images[seg.index]?.source" class="img-badge">
                      {{ badgeLabel(images[seg.index].source) }}
                    </div>
                    <!-- 悬停工具栏：缩放 / 替换 / 删除 -->
                    <div v-if="!loading" class="img-toolbar">
                      <button class="tb-btn" title="缩小" @click="resizeImage(seg.index, -10)">
                        <el-icon><ZoomOut /></el-icon>
                      </button>
                      <span class="tb-size">{{ images[seg.index]?.width || 100 }}%</span>
                      <button class="tb-btn" title="放大" @click="resizeImage(seg.index, 10)">
                        <el-icon><ZoomIn /></el-icon>
                      </button>
                      <span class="tb-div" />
                      <button class="tb-btn" title="图库替换" @click="replaceViaSearch(seg.index)">
                        <el-icon><Search /></el-icon>
                      </button>
                      <button class="tb-btn" title="上传替换" @click="replaceViaUpload(seg.index)">
                        <el-icon><Upload /></el-icon>
                      </button>
                      <button class="tb-btn danger" title="删除" @click="deleteImage(seg.index)">
                        <el-icon><Delete /></el-icon>
                      </button>
                    </div>
                  </div>
                  <div v-else class="article-image-loading">
                    <el-icon class="spin"><Loading /></el-icon>配图生成中...
                  </div>
                </template>
              </div>
            </template>
            <span v-if="loading" class="streaming-cursor">▋</span>

            <!-- 联网参考来源 -->
            <div v-if="references.length" class="refs" contenteditable="false">
              <div class="refs-title">📎 联网参考的爆款标题</div>
              <div v-for="(r, i) in references" :key="i" class="ref-item">· {{ r }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 隐藏的文件选择器：用于「上传替换」某张配图 -->
    <input ref="replaceFileInput" type="file" accept="image/jpeg,image/png,image/webp"
      style="display:none" @change="onReplaceFileChange" />

    <!-- 图片搜索弹窗 -->
    <el-dialog v-model="searchVisible" :title="replaceTargetIndex === null ? '搜索图库配图' : '选择一张图片替换'"
      width="720px" top="8vh">
      <div class="search-bar">
        <el-input v-model="searchQuery" placeholder="输入关键词，如：黄山 云海 / mountain sunrise"
          clearable @keyup.enter="doSearch">
          <template #append>
            <el-button :loading="searchLoading" @click="doSearch">
              <el-icon><Search /></el-icon>搜索
            </el-button>
          </template>
        </el-input>
      </div>
      <div class="search-hint">{{ replaceTargetIndex === null ? '支持中英文，英文关键词结果更丰富。点击图片选中/取消，可多选。' : '点击任意图片即可替换当前配图。' }}</div>

      <el-alert v-if="searchError" :title="searchError" type="warning" show-icon :closable="false" style="margin:10px 0" />

      <div v-if="searchLoading" class="search-state">
        <el-icon class="spin"><Loading /></el-icon><span>搜索中...</span>
      </div>
      <div v-else-if="searchResults.length" ref="searchGrid" class="search-grid" @scroll="onGridScroll">
        <div v-for="p in searchResults" :key="p.id"
          class="search-cell" :class="{ selected: replaceTargetIndex === null && isPicked(p) }"
          @click="onCellClick(p)">
          <el-image :src="p.thumb" fit="cover" class="search-thumb" lazy />
          <div class="search-check" v-if="replaceTargetIndex === null && isPicked(p)"><el-icon><Select /></el-icon></div>
          <div class="search-by">{{ p.photographer }}</div>
        </div>
        <!-- 底部加载状态：跨整行 -->
        <div class="search-more">
          <span v-if="searchLoadingMore"><el-icon class="spin"><Loading /></el-icon> 加载更多...</span>
          <span v-else-if="searchHasMore" class="more-hint">下滑加载更多</span>
          <span v-else class="more-hint">已经到底啦 · 共 {{ searchResults.length }} 张</span>
        </div>
      </div>
      <div v-else-if="searched" class="search-state">
        <el-icon><Picture /></el-icon><span>没有找到相关图片，换个关键词试试</span>
      </div>
      <div v-else class="search-state">
        <el-icon><Search /></el-icon><span>输入关键词开始搜索</span>
      </div>

      <template #footer>
        <template v-if="replaceTargetIndex === null">
          <span class="dialog-picked">已选 {{ pickedStock.length }} 张</span>
          <el-button @click="searchVisible = false">取消</el-button>
          <el-button type="primary" @click="searchVisible = false">
            确定使用（{{ pickedStock.length }}）
          </el-button>
        </template>
        <template v-else>
          <span class="dialog-picked">点击图片直接替换</span>
          <el-button @click="closeSearch">取消</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { generateWechatStream, listImageModels, searchStockImages } from '@/api/promotion.js'

defineOptions({ name: 'WechatPage' })

const form = ref({
  subject: '',
  style: '',
  articleType: '',
  wordCount: 1500,
  outline: '',
  autoGenerate: true,
  imageModel: 'gpt-image-2',
  useWebSearch: false,
})

const models = ref(['gpt-image-2', 'gpt-image-2-pro'])
const imageFiles = ref([])

// ── 图片搜索（Pexels，无限滚动） ──
const searchVisible = ref(false)
const searchQuery = ref('')
const searchLoading = ref(false)      // 首次搜索 loading
const searchLoadingMore = ref(false)  // 下滑加载更多 loading
const searched = ref(false)
const searchError = ref('')
const searchResults = ref([])
const searchPage = ref(1)
const searchHasMore = ref(false)
const SEARCH_PER_PAGE = 30
const searchGrid = ref(null)          // 结果网格容器，用于滚动监听
const pickedStock = ref([])       // 已选中的图库图片 { id, thumb, url, alt, photographer }
const replaceTargetIndex = ref(null)  // !=null 时弹窗为「替换第 N 张图」模式
const replaceFileInput = ref(null)    // 上传替换用的隐藏 file input

const loading = ref(false)
const error = ref('')
const markdown = ref('')          // 流式累积的正文（含 {{IMG:idx}} 占位）
const images = ref([])            // 下标 = 占位 idx
const references = ref([])
const previewRoot = ref(null)     // 预览容器 DOM，用于读取用户编辑后的纯文本

const hasContent = computed(() => markdown.value.trim().length > 0)

onMounted(async () => {
  try {
    const res = await listImageModels()
    if (res.models?.length) models.value = res.models
    if (res.default) form.value.imageModel = res.default
  } catch { /* 兜底列表 */ }
})

// ── 图片搜索交互 ──
function openSearch() {
  replaceTargetIndex.value = null   // 配图选择模式
  searchVisible.value = true
  // 首次打开时用文章主题预填关键词
  if (!searchQuery.value && form.value.subject) searchQuery.value = form.value.subject
}

function closeSearch() {
  searchVisible.value = false
  replaceTargetIndex.value = null
}

// 点击搜索结果：配图模式=多选切换；替换模式=直接替换并关闭
function onCellClick(p) {
  if (replaceTargetIndex.value === null) {
    togglePick(p)
  } else {
    applyImageAt(replaceTargetIndex.value, { url: p.url, source: 'stock', alt: p.alt })
    closeSearch()
  }
}

// 新搜索：重置分页，从第 1 页开始
async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) { ElMessage.warning('请输入搜索关键词'); return }
  searchLoading.value = true
  searchError.value = ''
  searchResults.value = []
  searchPage.value = 1
  searchHasMore.value = false
  try {
    const res = await searchStockImages(q, SEARCH_PER_PAGE, 1)
    const photos = res.photos || []
    searchResults.value = photos
    searched.value = true
    // 还有更多：本页拿满 且 未达总数
    searchHasMore.value = photos.length >= SEARCH_PER_PAGE
      && (!res.total || photos.length < res.total)
    if (res.error) searchError.value = res.error
  } catch (e) {
    searchError.value = e.message || '搜索失败，请稍后重试'
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

// 下滑加载更多：追加下一页，按 id 去重
async function loadMore() {
  if (searchLoadingMore.value || !searchHasMore.value || searchLoading.value) return
  const q = searchQuery.value.trim()
  if (!q) return
  searchLoadingMore.value = true
  try {
    const next = searchPage.value + 1
    const res = await searchStockImages(q, SEARCH_PER_PAGE, next)
    const photos = res.photos || []
    const seen = new Set(searchResults.value.map(x => x.id))
    const fresh = photos.filter(p => !seen.has(p.id))
    searchResults.value.push(...fresh)
    searchPage.value = next
    searchHasMore.value = photos.length >= SEARCH_PER_PAGE
      && (!res.total || searchResults.value.length < res.total)
  } catch {
    // 加载更多失败静默，保留已有结果
    searchHasMore.value = false
  } finally {
    searchLoadingMore.value = false
  }
}

// 网格滚动到接近底部时自动加载更多
function onGridScroll(e) {
  const el = e.target
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 120) loadMore()
}

function isPicked(p) {
  return pickedStock.value.some(x => x.id === p.id)
}
function togglePick(p) {
  const i = pickedStock.value.findIndex(x => x.id === p.id)
  if (i >= 0) pickedStock.value.splice(i, 1)
  else pickedStock.value.push(p)
}
function removePicked(i) {
  pickedStock.value.splice(i, 1)
}

// ── 正文配图的就地编辑（缩放 / 删除 / 替换）──
// 所有操作只改 images 数组，不动 markdown，避免正文重渲染丢失用户的文字编辑。

// 合并更新第 idx 张图的字段并触发响应式
function applyImageAt(idx, patch) {
  const cur = images.value[idx] || {}
  images.value[idx] = { ...cur, ...patch, deleted: false }
  images.value = [...images.value]
}

// 缩放：width 百分比，范围 30%~100%
function resizeImage(idx, delta) {
  const cur = images.value[idx] || {}
  const w = Math.max(30, Math.min(100, (cur.width || 100) + delta))
  applyImageAt(idx, { width: w })
}

function deleteImage(idx) {
  const cur = images.value[idx] || {}
  images.value[idx] = { ...cur, deleted: true }
  images.value = [...images.value]
}
function restoreImage(idx) {
  const cur = images.value[idx] || {}
  images.value[idx] = { ...cur, deleted: false }
  images.value = [...images.value]
}

// 图库替换：打开搜索弹窗，进入替换模式
function replaceViaSearch(idx) {
  replaceTargetIndex.value = idx
  searchVisible.value = true
  if (!searchQuery.value && form.value.subject) searchQuery.value = form.value.subject
}

// 上传替换：触发隐藏 file input，记住目标下标
function replaceViaUpload(idx) {
  replaceTargetIndex.value = idx
  replaceFileInput.value?.click()
}
function onReplaceFileChange(e) {
  const file = e.target.files?.[0]
  e.target.value = ''  // 允许再次选同一文件
  const idx = replaceTargetIndex.value
  replaceTargetIndex.value = null
  if (!file || idx === null) return
  if (file.size > 10 * 1024 * 1024) { ElMessage.warning('图片超过 10MB'); return }
  const reader = new FileReader()
  reader.onload = () => {
    applyImageAt(idx, { data_url: reader.result, url: null, source: 'upload' })
  }
  reader.readAsDataURL(file)
}

// 把 markdown 按 {{IMG:idx}} 占位切成 [html, image, html, ...] 片段
const renderedSegments = computed(() => {
  const src = markdown.value
  const re = /\{\{IMG:(\d+)\}\}/g
  const segs = []
  let last = 0
  let m
  while ((m = re.exec(src)) !== null) {
    const before = src.slice(last, m.index)
    if (before.trim()) segs.push({ type: 'html', html: marked.parse(before) })
    segs.push({ type: 'image', index: Number(m[1]) })
    last = m.index + m[0].length
  }
  const tail = src.slice(last)
  if (tail.trim()) segs.push({ type: 'html', html: marked.parse(tail) })
  return segs
})

function badgeLabel(source) {
  return { upload: '上传', stock: '图库', generated: 'AI 生成' }[source] || 'AI 生成'
}

function imgSrcFor(idx) {
  const img = images.value[idx]
  return img ? (img.data_url || img.url || '') : ''
}
// 已解析出图片的 src 列表（用于点击大图预览），跳过已删除
const allImageSrcs = computed(() =>
  images.value.filter(im => im && !im.deleted).map(im => im.data_url || im.url || '').filter(Boolean),
)
function previewIndexFor(idx) {
  const target = imgSrcFor(idx)
  return Math.max(0, allImageSrcs.value.indexOf(target))
}

async function generate() {
  if (!form.value.subject.trim()) { ElMessage.warning('请输入文章主题'); return }
  loading.value = true
  error.value = ''
  markdown.value = ''
  images.value = []
  references.value = []

  const fd = new FormData()
  fd.append('subject', form.value.subject)
  fd.append('style', form.value.style)
  fd.append('article_type', form.value.articleType)
  fd.append('word_count', String(form.value.wordCount))
  fd.append('outline', form.value.outline)
  fd.append('use_web_search', String(form.value.useWebSearch))
  fd.append('auto_generate', String(form.value.autoGenerate))
  fd.append('image_model', form.value.imageModel)
  for (const f of imageFiles.value) {
    if (f.raw) fd.append('images', f.raw)
  }
  // 搜索选中的图库图片（以 URL 形式随请求发送，插图顺序在上传图之后）
  if (pickedStock.value.length) {
    fd.append('stock_images', JSON.stringify(
      pickedStock.value.map(p => ({ url: p.url, alt: p.alt })),
    ))
  }

  await generateWechatStream(fd, {
    onDelta(content) { markdown.value += content },
    onImage(payload) {
      // payload: { index, data_url, url, source, alt }
      images.value[payload.index] = payload
      // 触发响应式更新（直接按下标赋值 Vue3 可侦测，但保险起见拷贝）
      images.value = [...images.value]
    },
    onFinal(payload) {
      if (payload.markdown) markdown.value = payload.markdown
      if (payload.images) images.value = payload.images
      references.value = payload.references || []
    },
    onDone() { loading.value = false },
    onError(err) {
      error.value = err.message || '推文生成失败，请稍后重试'
      loading.value = false
    },
  })
}

// 从渲染后的 DOM 读取纯文字（含用户的就地编辑），逐块按段落换行拼接
function extractPlainText() {
  const root = previewRoot.value
  if (!root) return ''
  const parts = []
  for (const block of root.querySelectorAll('.md-output')) {
    // 每个块级元素单独成段，保留标题/段落/列表间的换行
    const lines = []
    block.querySelectorAll('h1,h2,h3,h4,p,li,blockquote').forEach(el => {
      const t = el.innerText.trim()
      if (t) lines.push(t)
    })
    // 万一块内没有上述标签，兜底取整体文本
    parts.push(lines.length ? lines.join('\n\n') : block.innerText.trim())
  }
  return parts.filter(Boolean).join('\n\n').trim()
}

function copyText() {
  const text = extractPlainText()
  if (!text) { ElMessage.warning('暂无可复制的正文'); return }
  navigator.clipboard.writeText(text)
  ElMessage.success('正文已复制为纯文字（图片请在预览区右键或下载保存）')
}
</script>

<style scoped>
.promo-layout { display: grid; grid-template-columns: 380px 1fr; gap: 16px; min-height: 500px; }
.io-panel { display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.io-panel-header { padding: 12px 20px; border-bottom: 1px solid var(--color-border); font-weight: 500; font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; background: #fafafa; flex-shrink: 0; }
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }
.field-hint { font-size: 12px; color: #999; margin-top: 4px; line-height: 1.5; }

/* 已选图库图片缩略 */
.picked-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.picked-item { position: relative; width: 64px; height: 64px; }
.picked-thumb { width: 64px; height: 64px; border-radius: 6px; border: 1px solid var(--color-border); }
.picked-remove { position: absolute; top: -6px; right: -6px; background: #fff; border-radius: 50%; color: #f56c6c; cursor: pointer; font-size: 16px; }
.picked-remove:hover { color: #f23c3c; }

/* 搜索弹窗 */
.search-bar { margin-bottom: 6px; }
.search-hint { font-size: 12px; color: #999; margin-bottom: 4px; }
.search-state { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; height: 260px; color: #999; }
.search-state .el-icon { font-size: 32px; opacity: .5; }
.search-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; max-height: 420px; overflow-y: auto; padding: 4px; }
.search-cell { position: relative; cursor: pointer; border-radius: 8px; overflow: hidden; border: 2px solid transparent; transition: border-color .15s; }
.search-cell:hover { border-color: #c6e2ff; }
.search-cell.selected { border-color: var(--color-primary); }
.search-thumb { width: 100%; aspect-ratio: 1; display: block; }
.search-check { position: absolute; top: 4px; right: 4px; width: 22px; height: 22px; border-radius: 50%; background: var(--color-primary); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.search-by { position: absolute; bottom: 0; left: 0; right: 0; font-size: 10px; color: #fff; background: linear-gradient(transparent, rgba(0,0,0,.6)); padding: 8px 4px 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.search-more { grid-column: 1 / -1; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 12px 0 4px; font-size: 13px; color: #999; }
.search-more .more-hint { color: #bbb; }
.dialog-picked { float: left; font-size: 13px; color: var(--color-text-secondary); line-height: 32px; }

.wechat-preview { background: #fff; }
.md-output { font-size: 15px; color: #333; line-height: 1.8; }
.md-output :deep(h1) { font-size: 22px; font-weight: 700; margin: 8px 0 16px; }
.md-output :deep(h2) { font-size: 18px; font-weight: 600; margin: 20px 0 10px; padding-left: 10px; border-left: 4px solid #07c160; }
.md-output :deep(blockquote) { margin: 12px 0; padding: 10px 14px; background: #f6f8fa; border-left: 3px solid #07c160; color: #555; border-radius: 4px; }
.md-output :deep(p) { margin: 10px 0; }
.md-output :deep(ul), .md-output :deep(ol) { padding-left: 22px; }

.article-image { position: relative; margin: 16px 0; text-align: center; }
/* 图片外壳：宽度百分比可调（缩放），居中，最大不超过 480px */
.img-wrap { position: relative; display: inline-block; width: 100%; max-width: 480px; vertical-align: top; }
.wx-img { display: block; width: 100%; border-radius: 8px; border: 1px solid var(--color-border); overflow: hidden; }
/* 让内层 img 按原始比例完整显示，不裁剪、不限制高度 */
.wx-img :deep(.el-image__inner) { width: 100%; height: auto; display: block; object-fit: contain; }
.article-image-loading { display: flex; align-items: center; justify-content: center; gap: 8px; height: 180px; background: #f6f8fa; border-radius: 8px; color: #999; font-size: 13px; border: 1px dashed var(--color-border); }
.img-badge { position: absolute; top: 8px; right: 8px; font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(0,0,0,.55); color: #fff; }

/* 悬停工具栏 */
.img-toolbar { position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 2px; padding: 3px 6px; background: rgba(0,0,0,.62); border-radius: 8px; opacity: 0; transition: opacity .15s; }
.img-wrap:hover .img-toolbar { opacity: 1; }
.tb-btn { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border: none; background: transparent; color: #fff; cursor: pointer; border-radius: 5px; font-size: 15px; }
.tb-btn:hover { background: rgba(255,255,255,.2); }
.tb-btn.danger:hover { background: #f56c6c; }
.tb-size { color: #fff; font-size: 12px; min-width: 34px; text-align: center; }
.tb-div { width: 1px; height: 16px; background: rgba(255,255,255,.3); margin: 0 3px; }

/* 已删除占位条 */
.image-removed { display: flex; align-items: center; justify-content: center; gap: 8px; height: 72px; background: #f6f8fa; border: 1px dashed var(--color-border); border-radius: 8px; color: #999; font-size: 13px; }
.image-removed .link { color: var(--color-primary); cursor: pointer; }
.image-removed .link:hover { text-decoration: underline; }
.image-removed .sep { color: #ccc; }

.streaming-cursor { display: inline-block; animation: blink 0.8s step-end infinite; color: #07c160; font-weight: 700; }
@keyframes blink { 50% { opacity: 0; } }

/* 所见即所得编辑：正文块可点击编辑，聚焦时高亮 */
.editable-tip { display: inline-flex; align-items: center; gap: 3px; font-size: 12px; color: #999; margin-right: 4px; }
.md-output.editable { border-radius: 6px; transition: background .15s, box-shadow .15s; cursor: text; }
.md-output.editable:hover { background: #fafcfa; }
.md-output.editable:focus { outline: none; background: #fff; box-shadow: 0 0 0 2px #07c16033; }

.refs { margin-top: 18px; padding: 12px 14px; background: #f7f8fa; border-radius: 8px; }
.refs-title { font-size: 12px; color: #888; margin-bottom: 6px; }
.ref-item { font-size: 12px; color: #666; line-height: 1.7; }

.wip-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; height: 300px; color: var(--color-text-secondary); }
.wip-placeholder .el-icon { font-size: 36px; opacity: 0.5; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .promo-layout { grid-template-columns: 1fr; } }
</style>
