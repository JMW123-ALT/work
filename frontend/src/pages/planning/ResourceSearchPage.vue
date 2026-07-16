<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">资料查询</div>
      <div class="page-desc">在资源库或互联网中检索相关资料，加入策划上下文</div>
    </div>

    <div class="search-layout">
      <!-- 检索面板 -->
      <div class="work-card search-panel">
        <el-tabs v-model="searchSource">
          <el-tab-pane label="资源库" name="local" />
          <el-tab-pane label="互联网（预留）" name="internet" disabled />
        </el-tabs>

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
            <span class="param-label">返回条数</span>
            <el-slider v-model="topK" :min="1" :max="20" :step="1" style="flex:1;margin:0 12px" />
            <span class="param-value">{{ topK }}</span>
            <span class="param-label" style="margin-left:16px">最低置信度</span>
            <el-slider v-model="minConf" :min="0" :max="1" :step="0.05" style="flex:1;margin:0 12px" />
            <span class="param-value">{{ minConf.toFixed(2) }}</span>
          </div>
        </el-form>

        <el-alert v-if="error" :title="error" type="error" show-icon :closable="true" @close="error=''" style="margin-top:12px" />
      </div>

      <!-- 结果列表 -->
      <div class="search-results">
        <div v-if="loading" class="work-card">
          <el-skeleton :rows="5" animated />
        </div>

        <div v-else-if="!results.length && searched" class="work-card">
          <el-empty description="未找到相关资料，换个关键词试试" />
        </div>

        <template v-else>
          <div class="results-header" v-if="results.length">
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
              <el-button
                size="small"
                :type="selectedIds.has(i) ? 'success' : 'primary'"
                plain
                @click="toggleSelect(i)"
              >
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
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { searchResources } from '@/api/search.js'
import { useAppStore } from '@/stores/app.js'
import { useResourcesStore } from '@/stores/resources.js'

const appStore = useAppStore()
const resourcesStore = useResourcesStore()

const query = ref('')
const topK = ref(5)
const minConf = ref(0.7)
const searchSource = ref('local')
const loading = ref(false)
const error = ref('')
const results = ref([])
const searched = ref(false)
const permissionNotice = ref('')
const selectedIds = ref(new Set())

async function doSearch() {
  if (!query.value.trim()) return
  loading.value = true
  error.value = ''
  results.value = []
  searched.value = true
  selectedIds.value = new Set()
  try {
    const data = await searchResources({
      query: query.value.trim(),
      userType: appStore.currentUserType,
      topK: topK.value,
      minConfidence: minConf.value,
    })
    results.value = data.items || []
    permissionNotice.value = data.permissionNotice || ''
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function toggleSelect(idx) {
  const set = new Set(selectedIds.value)
  if (set.has(idx)) set.delete(idx)
  else set.add(idx)
  selectedIds.value = set
  const selected = [...set].map(i => results.value[i]?.text || '').filter(Boolean)
  resourcesStore.currentPlanningContext = selected.join('\n\n---\n\n')
}

function addAllToContext() {
  selectedIds.value = new Set(results.value.map((_, i) => i))
  resourcesStore.currentPlanningContext = results.value.map(r => r.text).join('\n\n---\n\n')
}
</script>

<style scoped>
.search-layout { display: flex; flex-direction: column; gap: 16px; }

.search-panel { padding: 16px 20px; }

.search-params {
  display: flex;
  align-items: center;
  margin-top: 12px;
  font-size: 13px;
  gap: 4px;
}
.param-label { color: var(--color-text-secondary); white-space: nowrap; }
.param-value { min-width: 36px; font-weight: 500; color: var(--color-primary); }

.results-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.result-card {
  padding: 14px 18px;
  margin-bottom: 10px;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}
.result-card.selected {
  border-color: #52c41a;
  box-shadow: 0 0 0 2px rgba(82,196,26,.15);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.result-theme { font-weight: 500; font-size: 14px; }

.result-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-meta { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
