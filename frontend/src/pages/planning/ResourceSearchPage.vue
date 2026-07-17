<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">资料查询</div>
      <div class="page-desc">
        在资源库中检索相关资料，加入策划上下文
        <el-switch
          v-model="webEnabled"
          active-text="联网搜索"
          inactive-text=""
          style="margin-left: 16px; vertical-align: middle"
        />
      </div>
    </div>

    <!-- 搜索框 — 跨左右共用 -->
    <div class="work-card search-bar-card">
      <el-form @submit.prevent="doSearch">
        <el-input
          v-model="query"
          placeholder="输入检索词，如：文旅 IP 打造策略、景区运营数据..."
          size="large"
          clearable
        >
          <template #append>
            <el-button type="primary" :loading="loading" @click="doSearch" native-type="submit">
              <el-icon><Search /></el-icon>检索
            </el-button>
          </template>
        </el-input>

        <div class="search-params">
          <span class="param-label">资料库 top-k</span>
          <el-slider v-model="topK" :min="1" :max="20" :step="1" style="width:120px;margin:0 10px" />
          <span class="param-value">{{ topK }}</span>
          <span class="param-label" style="margin-left:16px">最低置信度</span>
          <el-slider v-model="minConf" :min="0" :max="1" :step="0.05" style="width:120px;margin:0 10px" />
          <span class="param-value">{{ minConf.toFixed(2) }}</span>
        </div>
      </el-form>
      <el-alert v-if="error" :title="error" type="error" show-icon :closable="true" @close="error=''" style="margin-top:12px" />
    </div>

    <!-- 主体：联网关闭时单列；开启时左右分栏 -->
    <div :class="webEnabled ? 'split-layout' : 'single-layout'">

      <!-- ── 左：资料库检索结果 ── -->
      <div class="result-pane">
        <div class="pane-title" v-if="webEnabled">
          <el-icon><DataBoard /></el-icon> 资料库
        </div>

        <div v-if="loading" class="work-card">
          <el-skeleton :rows="4" animated />
        </div>

        <div v-else-if="!results.length && searched" class="work-card">
          <el-empty description="未找到相关资料，换个关键词试试" />
        </div>

        <template v-else-if="results.length">
          <div class="results-header">
            <span>找到 <strong>{{ results.length }}</strong> 条相关资料</span>
            <el-tag v-if="permissionNotice" type="warning" size="small">{{ permissionNotice }}</el-tag>
            <div style="flex:1" />
            <el-button size="small" plain @click="addAllToContext">全部加入策划上下文</el-button>
          </div>

          <div
            v-for="(item, i) in results"
            :key="i"
            class="result-card work-card"
            :class="{ selected: selectedIds.has(i) }"
          >
            <div class="result-header">
              <span class="result-theme">{{ item.culture_theme || item.category || `资料 ${i+1}` }}</span>
              <el-tag size="small" type="success">{{ (item.confidence * 100).toFixed(0) }}%</el-tag>
              <div style="flex:1" />
              <el-button size="small" :type="selectedIds.has(i) ? 'success' : 'primary'" plain @click="toggleSelect(i)">
                {{ selectedIds.has(i) ? '✓ 已加入' : '+ 加入上下文' }}
              </el-button>
            </div>
            <div class="result-text">{{ item.text }}</div>
            <div class="result-meta">
              <el-tag v-if="item.source" size="small" type="info">{{ item.source }}</el-tag>
              <el-tag v-if="item.category" size="small">{{ item.category }}</el-tag>
            </div>
          </div>
        </template>
      </div>

      <!-- ── 右：联网搜索结果（仅 webEnabled 时显示） ── -->
      <div v-if="webEnabled" class="result-pane web-pane">
        <div class="pane-title">
          <el-icon><Monitor /></el-icon> 联网搜索
          <el-tag v-if="webSearching" type="warning" size="small" style="margin-left:8px">搜索中...</el-tag>
        </div>

        <!-- 搜索结果条目卡片 -->
        <div v-if="webSources.length" class="web-sources">
          <a
            v-for="(s, i) in webSources"
            :key="i"
            :href="s.url"
            target="_blank"
            rel="noopener"
            class="web-source-card"
          >
            <div class="web-source-title">{{ s.title }}</div>
            <div class="web-source-snippet">{{ s.snippet }}</div>
            <div class="web-source-url">{{ s.url }}</div>
          </a>
        </div>

        <!-- LLM 综合回答 -->
        <div v-if="webAnswer || webSearching" class="work-card web-answer-card">
          <div class="web-answer-label">
            <el-icon><ChatLineRound /></el-icon> 大模型综合回答
          </div>
          <div class="web-answer-body" v-html="renderedWebAnswer"></div>
          <div v-if="webSearching" class="typing-dots">
            <span /><span /><span />
          </div>
        </div>

        <div v-else-if="!webSearching && searched" class="work-card">
          <el-empty description="点击检索后会同步联网搜索" :image-size="60" />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'
import { useAppStore } from '@/stores/app.js'
import { useResourcesStore } from '@/stores/resources.js'
import { searchResources } from '@/api/search.js'

const appStore = useAppStore()
const resourcesStore = useResourcesStore()

// 状态绑定到 store（跨页保留）
const query    = computed({ get: () => resourcesStore.searchQuery,      set: v => { resourcesStore.searchQuery = v } })
const topK     = computed({ get: () => resourcesStore.searchTopK,       set: v => { resourcesStore.searchTopK = v } })
const minConf  = computed({ get: () => resourcesStore.searchMinConf,    set: v => { resourcesStore.searchMinConf = v } })
const results  = computed({ get: () => resourcesStore.searchResults,    set: v => { resourcesStore.searchResults = v } })
const searched = computed({ get: () => resourcesStore.searchSearched,   set: v => { resourcesStore.searchSearched = v } })
const permissionNotice = computed({ get: () => resourcesStore.searchPermissionNotice, set: v => { resourcesStore.searchPermissionNotice = v } })
const selectedIds = computed({ get: () => resourcesStore.searchSelectedIds, set: v => { resourcesStore.searchSelectedIds = v } })

const loading = ref(false)
const error   = ref('')
const webEnabled   = ref(false)
const webSearching = ref(false)
const webSources   = ref([])
const webAnswer    = ref('')

const renderedWebAnswer = computed(() =>
  webAnswer.value ? marked.parse(webAnswer.value) : ''
)

async function doSearch() {
  if (!query.value.trim()) return
  loading.value = true
  error.value = ''
  resourcesStore.searchResults = []
  resourcesStore.searchSearched = true
  resourcesStore.searchSelectedIds = new Set()

  // 并行：资料库 + 联网（如果开启）
  const tasks = [_searchLocal()]
  if (webEnabled.value) tasks.push(_searchWeb(query.value.trim()))
  await Promise.allSettled(tasks)
}

async function _searchLocal() {
  try {
    const data = await searchResources({
      query: query.value.trim(),
      userType: appStore.currentUserType,
      topK: topK.value,
      minConfidence: minConf.value,
    })
    resourcesStore.searchResults = data.items || []
    resourcesStore.searchPermissionNotice = data.permissionNotice || ''
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function _searchWeb(q) {
  webSearching.value = true
  webSources.value = []
  webAnswer.value = ''

  let res
  try {
    res = await fetch(`/api/web-search/stream?q=${encodeURIComponent(q)}`)
  } catch {
    webSearching.value = false
    return
  }
  if (!res.ok || !res.body) { webSearching.value = false; return }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop()
      for (const block of blocks) {
        if (!block.trim()) continue
        let eventType = 'message', dataStr = ''
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) eventType = line.slice(6).trim()
          if (line.startsWith('data:')) dataStr = line.slice(5).trim()
        }
        if (!dataStr) continue
        try {
          const payload = JSON.parse(dataStr)
          if (eventType === 'sources') webSources.value = payload.items || []
          if (eventType === 'delta') webAnswer.value += payload.content || ''
          if (eventType === 'done') webSearching.value = false
        } catch { /* skip bad JSON */ }
      }
    }
  } catch { /* stream interrupted */ }
  webSearching.value = false
}

function toggleSelect(idx) {
  const set = new Set(resourcesStore.searchSelectedIds)
  if (set.has(idx)) set.delete(idx)
  else set.add(idx)
  resourcesStore.searchSelectedIds = set
  const selected = [...set].map(i => resourcesStore.searchResults[i]?.text || '').filter(Boolean)
  resourcesStore.currentPlanningContext = selected.join('\n\n---\n\n')
}

function addAllToContext() {
  resourcesStore.searchSelectedIds = new Set(resourcesStore.searchResults.map((_, i) => i))
  resourcesStore.currentPlanningContext = resourcesStore.searchResults.map(r => r.text).join('\n\n---\n\n')
}
</script>

<style scoped>
.search-bar-card { padding: 16px 20px; margin-bottom: 16px; }

.search-params {
  display: flex; align-items: center; margin-top: 12px;
  font-size: 13px; gap: 4px; flex-wrap: wrap;
}
.param-label { color: var(--color-text-secondary); white-space: nowrap; }
.param-value { min-width: 36px; font-weight: 500; color: var(--color-primary); }

/* 单/双列布局 */
.single-layout { display: flex; flex-direction: column; gap: 12px; }
.split-layout   { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }

.result-pane { display: flex; flex-direction: column; gap: 10px; }

.pane-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 600; color: var(--color-text-secondary);
  padding: 4px 0 8px;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 4px;
}

/* 资料库结果 */
.results-header {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: var(--color-text-secondary);
}

.result-card { padding: 14px 18px; transition: border-color .2s, box-shadow .2s; }
.result-card.selected { border-color: #52c41a; box-shadow: 0 0 0 2px rgba(82,196,26,.15); }
.result-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.result-theme { font-weight: 500; font-size: 14px; }
.result-text {
  font-size: 13px; color: var(--color-text-secondary); line-height: 1.6;
  margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 4;
  -webkit-box-orient: vertical; overflow: hidden;
}
.result-meta { display: flex; gap: 6px; flex-wrap: wrap; }

/* 联网面板 */
.web-pane { min-height: 200px; }

.web-sources { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }

.web-source-card {
  display: block; padding: 10px 14px;
  border: 1px solid var(--color-border); border-radius: 8px;
  background: var(--color-card-bg); text-decoration: none;
  transition: border-color .15s, box-shadow .15s;
}
.web-source-card:hover { border-color: var(--color-primary); box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.web-source-title { font-size: 13px; font-weight: 500; color: var(--color-primary); margin-bottom: 4px; }
.web-source-snippet {
  font-size: 12px; color: var(--color-text-secondary); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  margin-bottom: 4px;
}
.web-source-url { font-size: 11px; color: #52c41a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.web-answer-card { padding: 16px 18px; }
.web-answer-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: var(--color-text-secondary);
  margin-bottom: 10px;
}
.web-answer-body {
  font-size: 13px; line-height: 1.8; color: var(--color-text-primary);
}
.web-answer-body :deep(p)  { margin: 0 0 8px; }
.web-answer-body :deep(ul) { padding-left: 18px; margin: 4px 0; }
.web-answer-body :deep(li) { margin: 2px 0; }
.web-answer-body :deep(strong) { color: var(--color-text-primary); }

/* 打字动画 */
.typing-dots { display: flex; gap: 4px; padding-top: 8px; }
.typing-dots span {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--color-primary); opacity: 0.4;
  animation: bounce 1.2s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: .2s; }
.typing-dots span:nth-child(3) { animation-delay: .4s; }
@keyframes bounce { 0%,80%,100% { transform:translateY(0) } 40% { transform:translateY(-6px); opacity:1 } }

@media (max-width: 900px) {
  .split-layout { grid-template-columns: 1fr; }
}
</style>
