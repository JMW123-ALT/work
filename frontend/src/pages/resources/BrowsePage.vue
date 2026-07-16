<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">资料展示</div>
      <div class="page-desc">浏览已入库的所有资料，支持按权限、类型、关键词筛选</div>
    </div>

    <!-- 筛选栏 -->
    <div class="work-card filter-bar">
      <el-input
        v-model="filterText"
        placeholder="搜索标题或内容..."
        clearable
        style="width:280px"
        @input="onFilter"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>

      <el-radio-group v-model="filterPermission" @change="onFilter">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="internal">
          <el-icon><Lock /></el-icon> 对内
        </el-radio-button>
        <el-radio-button label="public">
          <el-icon><Unlock /></el-icon> 对外
        </el-radio-button>
      </el-radio-group>

      <el-select
        v-model="filterType"
        placeholder="资料类型"
        clearable
        style="width:130px"
        @change="onFilter"
      >
        <el-option label="策划方案" value="planning" />
        <el-option label="政策" value="policy" />
        <el-option label="数据" value="data" />
        <el-option label="其他" value="other" />
      </el-select>

      <el-select
        v-model="filterModality"
        placeholder="资料模态"
        clearable
        style="width:120px"
        @change="onFilter"
      >
        <el-option label="文本" value="text" />
        <el-option label="PDF" value="pdf" />
        <el-option label="图片" value="image" />
        <el-option label="Office" value="office" />
      </el-select>

      <div style="flex:1" />

      <el-button :loading="loading" plain @click="load">
        <el-icon><Refresh /></el-icon>刷新
      </el-button>

      <span class="doc-count">共 <strong>{{ filtered.length }}</strong> 条</span>
    </div>

    <!-- 权限提示条 -->
    <div class="permission-notice" v-if="filterPermission === 'internal'">
      <el-icon><Lock /></el-icon>
      当前仅显示<strong>对内资料</strong>，外部用户不可见
    </div>
    <div class="permission-notice public" v-else-if="filterPermission === 'public'">
      <el-icon><Unlock /></el-icon>
      当前仅显示<strong>对外资料</strong>，所有用户均可访问
    </div>

    <!-- 加载骨架 -->
    <div class="work-card" v-if="loading" style="padding:24px">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- 空状态 -->
    <div class="work-card" v-else-if="!filtered.length">
      <el-empty
        :description="allDocs.length ? '没有符合筛选条件的资料' : '暂无入库资料，前往资源库录入'"
      >
        <el-button type="primary" plain @click="$router.push('/resources/ingest')">
          去录入资料
        </el-button>
      </el-empty>
    </div>

    <!-- 资料列表 -->
    <div v-else class="doc-grid">
      <div
        v-for="doc in paged"
        :key="doc.source_id || doc.title"
        class="doc-card work-card"
        @click="openDetail(doc)"
      >
        <!-- 卡片头 -->
        <div class="doc-card-header">
          <el-icon class="doc-type-icon" :class="modalityClass(doc.modality)">
            <component :is="modalityIcon(doc.modality)" />
          </el-icon>
          <div class="doc-card-title" :title="doc.title">{{ doc.title }}</div>
          <el-tag
            size="small"
            :type="doc.permission_level === 'public' ? 'success' : 'warning'"
            class="permission-tag"
          >
            <el-icon style="margin-right:2px">
              <Unlock v-if="doc.permission_level === 'public'" />
              <Lock v-else />
            </el-icon>
            {{ doc.permission_level === 'public' ? '对外' : '对内' }}
          </el-tag>
        </div>

        <!-- 内容摘要 -->
        <div class="doc-card-content">{{ excerpt(doc.content) }}</div>

        <!-- 底部元数据 -->
        <div class="doc-card-footer">
          <el-tag size="small" type="info">{{ typeLabel(doc.object_type) }}</el-tag>
          <el-tag size="small">{{ doc.modality || 'text' }}</el-tag>
          <span class="doc-chunks">{{ doc.chunk_count || 0 }} chunks</span>
          <span class="doc-status" :class="statusClass(doc.extraction_status)">
            {{ doc.extraction_status || 'parsed' }}
          </span>
        </div>

        <div class="doc-card-time" v-if="doc.updated_at">
          {{ formatTime(doc.updated_at) }}
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination-bar" v-if="filtered.length > pageSize">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="filtered.length"
        layout="prev, pager, next, total"
        background
        small
      />
    </div>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailVisible"
      :title="detailDoc?.title"
      size="520px"
      direction="rtl"
    >
      <template v-if="detailDoc">
        <!-- 权限徽标 -->
        <div class="detail-badges">
          <el-tag :type="detailDoc.permission_level === 'public' ? 'success' : 'warning'" size="large">
            <el-icon><Unlock v-if="detailDoc.permission_level === 'public'" /><Lock v-else /></el-icon>
            {{ detailDoc.permission_level === 'public' ? '对外公开' : '仅对内' }}
          </el-tag>
          <el-tag type="info">{{ typeLabel(detailDoc.object_type) }}</el-tag>
          <el-tag>{{ detailDoc.modality || 'text' }}</el-tag>
          <el-tag :type="statusTagType(detailDoc.extraction_status)">
            {{ detailDoc.extraction_status || 'parsed' }}
          </el-tag>
        </div>

        <el-divider />

        <!-- 基本信息 -->
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="资料 ID" :span="2">
            <span class="mono-text">{{ detailDoc.source_id || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="向量 chunks">{{ detailDoc.chunk_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="文件名">{{ detailDoc.file_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">
            {{ detailDoc.file_size ? formatSize(detailDoc.file_size) : '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="MIME">{{ detailDoc.mime_type || '—' }}</el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">
            {{ formatTime(detailDoc.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 正文 -->
        <div class="detail-section-title">正文内容</div>
        <div class="detail-content">{{ detailDoc.content || '（无正文内容）' }}</div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { listDocuments } from '@/api/resources.js'

const loading = ref(false)
const allDocs = ref([])
const filterText = ref('')
const filterPermission = ref('')
const filterType = ref('')
const filterModality = ref('')
const page = ref(1)
const pageSize = 18
const detailVisible = ref(false)
const detailDoc = ref(null)

// 筛选逻辑
const filtered = computed(() => {
  return allDocs.value.filter(doc => {
    if (filterPermission.value && doc.permission_level !== filterPermission.value) return false
    if (filterType.value && doc.object_type !== filterType.value) return false
    if (filterModality.value && (doc.modality || 'text') !== filterModality.value) return false
    if (filterText.value.trim()) {
      const kw = filterText.value.trim().toLowerCase()
      return (doc.title || '').toLowerCase().includes(kw) ||
             (doc.content || '').toLowerCase().includes(kw)
    }
    return true
  })
})

const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

function onFilter() { page.value = 1 }

async function load() {
  loading.value = true
  try {
    const data = await listDocuments()
    allDocs.value = data.items || []
  } catch {
    allDocs.value = []
  } finally {
    loading.value = false
  }
}

function openDetail(doc) {
  detailDoc.value = doc
  detailVisible.value = true
}

// ── 工具函数 ──
function excerpt(text = '') {
  const clean = text.replace(/\s+/g, ' ').trim()
  return clean.length > 100 ? clean.slice(0, 100) + '…' : clean || '（暂无摘要）'
}

function formatTime(t) {
  if (!t) return '—'
  try { return new Date(t).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' }) } catch { return t }
}

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const typeMap = { planning: '策划方案', policy: '政策', data: '数据', other: '其他' }
function typeLabel(t) { return typeMap[t] || t || '未分类' }

function modalityIcon(m) {
  const map = { pdf: 'Document', image: 'Picture', office: 'Paperclip', text: 'EditPen' }
  return map[m] || 'EditPen'
}

function modalityClass(m) {
  const map = { pdf: 'icon-pdf', image: 'icon-image', office: 'icon-office', text: 'icon-text' }
  return map[m] || 'icon-text'
}

function statusClass(s) {
  if (s === 'failed') return 'status-failed'
  if (s === 'processing') return 'status-processing'
  return 'status-ok'
}

function statusTagType(s) {
  if (s === 'failed') return 'danger'
  if (s === 'processing') return 'warning'
  return 'success'
}

onMounted(load)
</script>

<style scoped>
/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px 20px;
  margin-bottom: 12px;
}

.doc-count { font-size: 13px; color: var(--color-text-muted); white-space: nowrap; }

/* 权限提示条 */
.permission-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  font-size: 13px;
  color: #d46b08;
  margin-bottom: 12px;
}

.permission-notice.public {
  background: #f6ffed;
  border-color: #b7eb8f;
  color: #389e0d;
}

/* 文档卡片网格 */
.doc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.doc-card {
  padding: 16px 18px;
  cursor: pointer;
  transition: all var(--transition-base);
  border: 1px solid var(--color-border);
}

.doc-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.12);
  transform: translateY(-2px);
}

/* 卡片头 */
.doc-card-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
}

.doc-type-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 2px;
}
.icon-pdf    { color: #ff4d4f; }
.icon-image  { color: #52c41a; }
.icon-office { color: #faad14; }
.icon-text   { color: var(--color-primary); }

.doc-card-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.permission-tag { flex-shrink: 0; }

/* 摘要 */
.doc-card-content {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 58px;
}

/* 底部 */
.doc-card-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.doc-chunks {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-left: auto;
}

.doc-status { font-size: 11px; padding: 1px 6px; border-radius: 3px; }
.status-ok         { background: #f6ffed; color: #52c41a; }
.status-failed     { background: #fff2f0; color: #ff4d4f; }
.status-processing { background: #fffbe6; color: #faad14; animation: pulse 1.5s infinite; }

@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:.5 } }

.doc-card-time {
  font-size: 11px;
  color: var(--color-text-muted);
  text-align: right;
}

/* 分页 */
.pagination-bar {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

/* 详情抽屉 */
.detail-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.detail-section-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.detail-content {
  font-size: 13px;
  line-height: 1.8;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  background: #fafafa;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px 14px;
  max-height: 400px;
  overflow-y: auto;
}

.mono-text {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: var(--color-text-muted);
}
</style>
