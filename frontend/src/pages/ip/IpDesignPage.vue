<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">文创设计</div>
      <div class="page-desc">IP形象设定、故事构建，基于 AI Agent 自动检索资料并生成方案</div>
    </div>

    <div class="ip-layout">
      <!-- 左侧输入 -->
      <div class="io-panel work-card">
        <div class="io-panel-header">
          <el-icon><EditPen /></el-icon>输入需求
        </div>
        <div class="io-panel-body">
          <!-- 子功能 tab -->
          <el-tabs v-model="activeTab" class="ip-tabs">
            <el-tab-pane label="IP形象" name="ip" />
            <el-tab-pane label="故事设定" name="story" />
          </el-tabs>

          <el-form :model="form" label-position="top" class="ip-form">
            <el-form-item label="需求描述" required>
              <el-input
                v-model="form.query"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 8 }"
                :placeholder="tabPlaceholder"
              />
            </el-form-item>

            <el-form-item label="关联策划案（可选）">
              <el-input
                v-model="form.planningContext"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 4 }"
                placeholder="粘贴或输入策划案摘要，Agent 会将其纳入创作上下文"
              />
            </el-form-item>

            <el-form-item label="关联资源库（可选）">
              <el-input
                v-model="form.resourceContext"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 4 }"
                placeholder="粘贴相关资料片段，或从资源库检索后复制到此处"
              />
            </el-form-item>

            <el-form-item>
              <div class="form-params">
                <div class="param-item">
                  <span class="param-label">召回数量</span>
                  <el-slider v-model="form.topK" :min="1" :max="20" :step="1" :marks="{ 5: '5', 10: '10' }" style="flex:1" />
                  <span class="param-value">{{ form.topK }}</span>
                </div>
              </div>
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              :loading="loading"
              :disabled="!form.query.trim()"
              @click="generate"
              style="width:100%"
            >
              <el-icon><MagicStick /></el-icon>
              {{ loading ? '生成中...' : '生成方案' }}
            </el-button>
          </el-form>
        </div>
      </div>

      <!-- 右侧输出 -->
      <div class="io-panel work-card">
        <div class="io-panel-header">
          <el-icon><Document /></el-icon>生成结果
          <div style="flex:1" />
          <el-tag v-if="result.status" :type="statusType" size="small">{{ result.status }}</el-tag>
        </div>
        <div class="io-panel-body">
          <!-- 空状态 -->
          <div v-if="!result.final_answer && !loading && !error" class="wip-placeholder">
            <el-icon><MagicStick /></el-icon>
            <span>填写需求后点击"生成方案"</span>
          </div>

          <!-- 加载中 -->
          <div v-else-if="loading" class="loading-state">
            <el-icon class="spin"><Loading /></el-icon>
            <span>AI 正在检索资料并生成方案，请稍候...</span>
          </div>

          <!-- 错误 -->
          <el-alert v-else-if="error" :title="error" type="error" show-icon :closable="false" style="margin-bottom:16px" />

          <!-- 主结果 -->
          <template v-else>
            <div class="result-answer md-output" v-html="renderedAnswer" />

            <!-- warnings -->
            <div v-if="result.warnings?.length" class="result-warnings">
              <el-icon><Warning /></el-icon>
              <span v-for="w in result.warnings" :key="w" class="warning-text">{{ w }}</span>
            </div>

            <!-- evidence 折叠 -->
            <el-collapse v-if="result.evidence?.length" class="evidence-collapse">
              <el-collapse-item>
                <template #title>
                  <el-icon><InfoFilled /></el-icon>
                  引用资料（{{ result.evidence.length }} 条）
                </template>
                <div
                  v-for="(item, i) in result.evidence"
                  :key="i"
                  class="evidence-item"
                >
                  <div class="evidence-header">
                    <span class="evidence-theme">{{ item.culture_theme || item.source || `资料 ${i + 1}` }}</span>
                    <el-tag size="small" type="info">{{ (item.confidence * 100).toFixed(0) }}%</el-tag>
                  </div>
                  <div class="evidence-text">{{ item.text?.slice(0, 200) }}{{ item.text?.length > 200 ? '...' : '' }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import { runAgent } from '@/api/chat.js'
import { useAppStore } from '@/stores/app.js'

const appStore = useAppStore()
const activeTab = ref('ip')
const loading = ref(false)
const error = ref('')
const result = ref({})

const form = ref({
  query: '',
  planningContext: '',
  resourceContext: '',
  topK: 5,
})

const tabPlaceholder = computed(() =>
  activeTab.value === 'ip'
    ? '描述 IP 形象需求，如：为一个以黄山为原型的文旅项目设计主 IP 形象，需要有亲切感，适合全年龄段...'
    : '描述故事设定需求，如：为 IP 形象构建背景故事，主题是人与自然的和谐，有民俗文化元素...'
)

const renderedAnswer = computed(() => {
  if (!result.value.final_answer) return ''
  return marked.parse(result.value.final_answer)
})

const statusType = computed(() => {
  const map = { ok: 'success', partial: 'warning', blocked: 'danger' }
  return map[result.value.status] || 'info'
})

async function generate() {
  if (!form.value.query.trim()) return
  loading.value = true
  error.value = ''
  result.value = {}

  let q = form.value.query.trim()
  if (form.value.planningContext.trim()) q += `\n\n【策划案背景】${form.value.planningContext.trim()}`
  if (form.value.resourceContext.trim()) q += `\n\n【参考资料】${form.value.resourceContext.trim()}`

  try {
    result.value = await runAgent({
      query: q,
      userType: appStore.currentUserType,
      topK: form.value.topK,
    })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ip-layout {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 16px;
  height: calc(100vh - var(--topbar-height) - 100px);
}

.io-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

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
  border-radius: var(--radius-card) var(--radius-card) 0 0;
}

.io-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.ip-form { margin-top: 8px; }

.form-params { display: flex; flex-direction: column; gap: 12px; }

.param-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}
.param-label { color: var(--color-text-secondary); white-space: nowrap; min-width: 56px; }
.param-value { min-width: 28px; text-align: right; font-weight: 500; color: var(--color-primary); }

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px;
  color: var(--color-text-muted);
}
.spin { font-size: 28px; animation: spin 1s linear infinite; color: var(--color-primary); }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.result-answer { margin-bottom: 16px; }

.result-warnings {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #faad14;
  margin-bottom: 12px;
}
.warning-text { color: var(--color-text-muted); }

.evidence-collapse { margin-top: 8px; }
:deep(.evidence-collapse .el-collapse-item__header) {
  font-size: 12px;
  color: var(--color-text-muted);
  gap: 4px;
}

.evidence-item {
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
  margin-bottom: 8px;
  border: 1px solid var(--color-border);
}

.evidence-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.evidence-theme { font-size: 12px; font-weight: 500; color: var(--color-text-primary); }

.evidence-text { font-size: 12px; color: var(--color-text-secondary); line-height: 1.6; }

@media (max-width: 900px) {
  .ip-layout { grid-template-columns: 1fr; height: auto; }
}
</style>
