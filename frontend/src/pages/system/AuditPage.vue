<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">操作审计</div>
      <div class="page-desc">查看系统操作日志，追踪所有入库、检索、生成行为</div>
    </div>

    <div class="work-card">
      <div class="audit-toolbar">
        <el-button :loading="loading" @click="load" type="primary" plain>
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
        <span class="audit-count">共 {{ items.length }} 条记录</span>
      </div>

      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" style="margin-bottom:16px" />

      <el-skeleton v-if="loading" :rows="6" animated />

      <el-table
        v-else
        :data="pagedItems"
        stripe
        border
        style="width:100%"
        row-key="trace_id"
        :empty-text="items.length ? '' : '暂无审计记录'"
      >
        <el-table-column label="操作时间" prop="time" width="180" sortable>
          <template #default="{ row }">
            <span style="font-size:12px;color:var(--color-text-secondary)">{{ formatTime(row.time) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作类型" prop="action" width="120">
          <template #default="{ row }">
            <el-tag :type="actionTagType(row.action)" size="small">{{ row.action }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="用户类型" prop="user_type" width="100">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.user_type || '-' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Trace ID" prop="trace_id" width="200">
          <template #default="{ row }">
            <span class="trace-id" :title="row.trace_id">{{ row.trace_id || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag :type="row.detail?.status === 'ok' || row.detail?.success ? 'success' : 'info'" size="small">
              {{ row.detail?.status || '—' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="详情" min-width="200">
          <template #default="{ row }">
            <el-button link size="small" @click="showDetail(row)">
              <el-icon><View /></el-icon>查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="audit-pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="items.length"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          small
        />
      </div>
    </div>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="操作详情" width="600px" draggable>
      <pre class="detail-json">{{ detailJson }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getAuditLog } from '@/api/audit.js'

const loading = ref(false)
const error = ref('')
const items = ref([])
const page = ref(1)
const pageSize = ref(20)
const detailVisible = ref(false)
const detailJson = ref('')

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getAuditLog()
    items.value = (data.items || []).reverse() // 最新在前
  } catch (e) {
    error.value = `加载审计日志失败：${e.message}`
    items.value = []
  } finally {
    loading.value = false
  }
}

function formatTime(t) {
  if (!t) return '-'
  try { return new Date(t).toLocaleString('zh-CN') } catch { return t }
}

function actionTagType(action) {
  const map = { ingest: 'primary', search: 'success', chat: 'warning', audit: 'info' }
  return map[action] || 'info'
}

function showDetail(row) {
  detailJson.value = JSON.stringify(row.detail || row, null, 2)
  detailVisible.value = true
}

onMounted(load)
</script>

<style scoped>
.audit-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.audit-count { font-size: 13px; color: var(--color-text-muted); }
.trace-id {
  font-size: 11px;
  font-family: 'SF Mono', monospace;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  max-width: 180px;
}
.audit-pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
.detail-json {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 16px;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  overflow-x: auto;
  max-height: 500px;
  overflow-y: auto;
  white-space: pre-wrap;
}
</style>
