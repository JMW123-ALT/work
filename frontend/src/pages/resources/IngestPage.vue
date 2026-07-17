<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">资源库录入</div>
      <div class="page-desc">将文本资料或文件入库，支持对内 / 对外权限控制</div>
    </div>

    <div class="ingest-layout">
      <!-- 录入表单 -->
      <div class="work-card ingest-form-card">
        <el-tabs v-model="ingestMode" class="ingest-tabs">

          <!-- ── 文本录入 ── -->
          <el-tab-pane label="文本录入" name="text">
            <el-form :model="textForm" label-position="top" ref="textFormRef" :rules="textRules">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="标题" prop="title" required>
                    <el-input v-model="textForm.title" placeholder="资料标题" />
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="资料类型">
                    <el-select v-model="textForm.objectType" style="width:100%">
                      <el-option label="策划方案" value="planning" />
                      <el-option label="政策" value="policy" />
                      <el-option label="数据" value="data" />
                      <el-option label="其他" value="other" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="权限范围">
                    <el-select v-model="textForm.permissionLevel" style="width:100%">
                      <el-option label="对内" value="internal" />
                      <el-option label="对外" value="public" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="正文内容" prop="content" required>
                <el-input
                  v-model="textForm.content"
                  type="textarea"
                  :autosize="{ minRows: 8, maxRows: 18 }"
                  placeholder="粘贴或输入资料正文..."
                />
              </el-form-item>
              <div class="form-footer">
                <el-button type="primary" :loading="loading" @click="submitText" :disabled="loading">
                  <el-icon><Upload /></el-icon>入库
                </el-button>
              </div>
            </el-form>
          </el-tab-pane>

          <!-- ── 文件上传 ── -->
          <el-tab-pane label="文件上传" name="file">
            <el-form :model="fileForm" label-position="top">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="标题（选填，留空则自动使用文件名）">
                    <el-input v-model="fileForm.title" placeholder="多文件时留空，各用文件名" />
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="资料类型">
                    <el-select v-model="fileForm.objectType" style="width:100%">
                      <el-option label="策划方案" value="planning" />
                      <el-option label="政策" value="policy" />
                      <el-option label="数据" value="data" />
                      <el-option label="其他" value="other" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="权限范围">
                    <el-select v-model="fileForm.permissionLevel" style="width:100%">
                      <el-option label="对内" value="internal" />
                      <el-option label="对外" value="public" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="选择文件">
                <el-upload
                  drag
                  multiple
                  :auto-upload="false"
                  :show-file-list="false"
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,.txt,.md"
                  :on-change="onFileAdd"
                  class="file-upload-area"
                >
                  <el-icon class="upload-icon"><UploadFilled /></el-icon>
                  <div class="upload-text">拖拽文件至此处，或 <em>点击选择</em></div>
                  <div class="upload-hint">
                    支持 PDF · Word · Excel · PPT · 图片 · 文本，自动识别格式
                  </div>
                </el-upload>
              </el-form-item>

              <div v-if="fileList.length" class="file-preview-list">
                <div class="file-preview-header">
                  <span>已选 {{ fileList.length }} 个文件</span>
                  <el-button link size="small" type="danger" @click="fileList = []">全部清空</el-button>
                </div>
                <div v-for="(f, idx) in fileList" :key="idx" class="file-preview-item">
                  <el-icon class="file-type-icon" :class="modalityClass(f.modality)">
                    <component :is="modalityIcon(f.modality)" />
                  </el-icon>
                  <div class="file-info">
                    <span class="file-name" :title="f.raw.name">{{ f.raw.name }}</span>
                    <span class="file-size">{{ formatSize(f.raw.size) }}</span>
                  </div>
                  <el-tag size="small" :type="modalityTagType(f.modality)" class="modality-tag">
                    {{ modalityLabel(f.modality) }}
                  </el-tag>
                  <el-button link size="small" type="danger" @click="removeFile(idx)" class="file-remove">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </div>

              <div class="form-footer">
                <el-button
                  type="primary"
                  :loading="loading"
                  @click="submitFile"
                  :disabled="!fileList.length || loading"
                  size="large"
                >
                  <el-icon><Upload /></el-icon>
                  上传入库（{{ fileList.length }} 个文件）
                </el-button>
              </div>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 右侧：状态 + 文档列表 -->
      <div class="ingest-right">
        <el-alert v-if="successItems.length" type="success" show-icon :closable="false" style="margin-bottom:16px">
          <template #title>已提交 {{ successItems.length }} 条资料（后台索引中）</template>
          <div v-for="item in successItems" :key="item.document_id || item.title" class="success-item">
            <el-icon><Document /></el-icon>
            <span>{{ item.title }}</span>
            <el-tag size="small" :type="modalityTagType(item.modality)">{{ modalityLabel(item.modality) }}</el-tag>
            <el-tag size="small" :type="statusTagType(item.status)">{{ statusLabel(item.status) }}</el-tag>
          </div>
        </el-alert>

        <el-alert v-if="errorMsg" type="error" :title="errorMsg" show-icon closable @close="errorMsg=''" style="margin-bottom:16px" />

        <!-- 已入库文档列表 -->
        <div class="work-card doc-list-card">
          <div class="doc-list-header">
            <span class="doc-list-title">已入库资料</span>
            <el-button link size="small" @click="loadDocs"><el-icon><Refresh /></el-icon>刷新</el-button>
          </div>
          <div v-if="docsLoading" class="docs-loading">
            <el-icon class="spin"><Loading /></el-icon> 加载中...
          </div>
          <div v-else-if="!docs.length" class="docs-empty">暂无资料，开始录入后将在此显示</div>
          <div v-else class="doc-items">
            <div v-for="doc in docs" :key="doc.document_id || doc.source_id" class="doc-item">
              <div class="doc-item-main">
                <el-icon class="doc-icon" :class="modalityClass(doc.modality)">
                  <component :is="modalityIcon(doc.modality)" />
                </el-icon>
                <span class="doc-title">{{ doc.title }}</span>
                <div class="doc-tags">
                  <el-tag size="small" :type="modalityTagType(doc.modality)">{{ modalityLabel(doc.modality) }}</el-tag>
                  <el-tag size="small" :type="doc.permission_level === 'public' ? 'success' : 'warning'">
                    {{ doc.permission_level === 'public' ? '对外' : '对内' }}
                  </el-tag>
                  <!-- v2 processing status -->
                  <el-tag size="small" :type="statusTagType(doc.status)">{{ statusLabel(doc.status) }}</el-tag>
                </div>
              </div>
              <div v-if="doc.error_message" class="doc-error">
                <el-icon><Warning /></el-icon> {{ doc.error_message }}
              </div>
              <div class="doc-meta">
                <span v-if="doc.updated_at">{{ doc.updated_at?.slice(0,16) }}</span>
                <span v-if="doc.file_size"> · {{ formatSize(doc.file_size) }}</span>
              </div>
              <!-- Actions: retry for failed, delete for any -->
              <div class="doc-actions">
                <el-button
                  v-if="doc.status === 'failed' || doc.status === 'queued'"
                  link size="small" type="primary"
                  :loading="retrying[doc.document_id]"
                  @click="retryDoc(doc)"
                >
                  <el-icon><RefreshRight /></el-icon>重试
                </el-button>
                <el-button
                  link size="small" type="danger"
                  :loading="deleting[doc.document_id]"
                  @click="deleteDoc(doc)"
                >
                  <el-icon><Delete /></el-icon>删除
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ingestText, ingestFile, listDocuments, retryDocument, deleteDocument } from '@/api/resources.js'
import { useAppStore } from '@/stores/app.js'

const appStore = useAppStore()
const ingestMode = ref('text')
const loading = ref(false)
const successItems = ref([])
const errorMsg = ref('')
const docs = ref([])
const docsLoading = ref(false)
const fileList = ref([])
const textFormRef = ref(null)
const retrying = ref({})
const deleting = ref({})

const textForm = ref({ title: '', content: '', objectType: 'other', permissionLevel: 'internal' })
const fileForm = ref({ title: '', objectType: 'other', permissionLevel: 'internal' })

const textRules = {
  title:   [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入正文内容', trigger: 'blur' }],
}

// ── 自动识别文件类型 ──────────────────────────────────────────────────
const EXT_MAP = {
  pdf:  'pdf',
  doc: 'office', docx: 'office',
  xls: 'office', xlsx: 'office',
  ppt: 'office', pptx: 'office',
  jpg: 'image',  jpeg: 'image', png: 'image',
  gif: 'image',  webp: 'image', bmp: 'image',
  txt: 'text',   md: 'text',
}

function detectModality(file) {
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  return EXT_MAP[ext] || 'text'
}

function onFileAdd(file) {
  if (file.raw) fileList.value.push({ raw: file.raw, modality: detectModality(file.raw) })
}

function removeFile(idx) { fileList.value.splice(idx, 1) }

// ── 类型显示 ──────────────────────────────────────────────────────────
const MODALITY_LABEL = { pdf: 'PDF', office: 'Office', image: '图片', text: '文本' }
const MODALITY_TAG   = { pdf: 'danger', office: 'warning', image: 'success', text: '' }
const MODALITY_ICON  = { pdf: 'Document', office: 'Paperclip', image: 'Picture', text: 'EditPen' }
const MODALITY_CLASS = { pdf: 'icon-pdf', office: 'icon-office', image: 'icon-image', text: 'icon-text' }

function modalityLabel(m) { return MODALITY_LABEL[m] || m || 'text' }
function modalityTagType(m) { return MODALITY_TAG[m] ?? '' }
function modalityIcon(m)  { return MODALITY_ICON[m] || 'EditPen' }
function modalityClass(m) { return MODALITY_CLASS[m] || 'icon-text' }

// ── 处理状态显示 ──────────────────────────────────────────────────────
const STATUS_LABEL = {
  queued: '排队中', parsing: '解析中', embedding: '向量化',
  ready: '可检索', failed: '失败', deleting: '删除中', deleted: '已删除',
}
const STATUS_TAG = {
  queued: 'info', parsing: 'warning', embedding: 'warning',
  ready: 'success', failed: 'danger', deleting: 'info', deleted: 'info',
}

function statusLabel(s) { return STATUS_LABEL[s] || s || '-' }
function statusTagType(s) { return STATUS_TAG[s] ?? '' }

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// ── 数据加载 ──────────────────────────────────────────────────────────
async function loadDocs() {
  docsLoading.value = true
  try {
    const data = await listDocuments()
    docs.value = data.items || []
  } catch { docs.value = [] }
  finally { docsLoading.value = false }
}

// ── 提交文本 ──────────────────────────────────────────────────────────
async function submitText() {
  await textFormRef.value?.validate()
  loading.value = true
  successItems.value = []
  errorMsg.value = ''
  try {
    const data = await ingestText({
      title: textForm.value.title,
      content: textForm.value.content,
      objectType: textForm.value.objectType,
      permissionLevel: textForm.value.permissionLevel,
      ingestRole: appStore.currentUserType === 'visitor' ? 'none' : 'admin',
    })
    successItems.value = data.item ? [data.item] : (data.items || [])
    textForm.value.title = ''
    textForm.value.content = ''
    await loadDocs()
  } catch (e) { errorMsg.value = e.message }
  finally { loading.value = false }
}

// ── 提交文件 ──────────────────────────────────────────────────────────
async function submitFile() {
  if (!fileList.value.length) return
  loading.value = true
  successItems.value = []
  errorMsg.value = ''
  try {
    const form = new FormData()
    form.append('title', fileForm.value.title)
    form.append('object_type', fileForm.value.objectType)
    form.append('permission_level', fileForm.value.permissionLevel)
    form.append('ingest_role', appStore.currentUserType === 'visitor' ? 'none' : 'admin')
    form.append('operator', 'local-admin')
    fileList.value.forEach(f => form.append('files', f.raw))
    const data = await ingestFile(form)
    successItems.value = data.items || (data.item ? [data.item] : [])
    fileList.value = []
    await loadDocs()
  } catch (e) { errorMsg.value = e.message }
  finally { loading.value = false }
}

// ── 重试 ──────────────────────────────────────────────────────────────
async function retryDoc(doc) {
  const id = doc.document_id || doc.source_id
  retrying.value[id] = true
  try {
    await retryDocument(id)
    await loadDocs()
  } catch (e) { errorMsg.value = e.message }
  finally { retrying.value[id] = false }
}

// ── 删除 ──────────────────────────────────────────────────────────────
async function deleteDoc(doc) {
  const id = doc.document_id || doc.source_id
  if (!confirm(`确认删除「${doc.title}」？删除后无法恢复。`)) return
  deleting.value[id] = true
  try {
    await deleteDocument(id)
    await loadDocs()
  } catch (e) { errorMsg.value = e.message }
  finally { deleting.value[id] = false }
}

onMounted(loadDocs)
</script>

<style scoped>
.ingest-layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
  align-items: start;
}

.ingest-form-card { padding: 20px 24px; }
.form-footer { margin-top: 12px; }

.file-upload-area { width: 100%; }
.upload-icon { font-size: 40px; color: #c0c4cc; margin-bottom: 8px; }
.upload-text { font-size: 14px; color: var(--color-text-secondary); }
.upload-text em { color: var(--color-primary); font-style: normal; }
.upload-hint { font-size: 12px; color: var(--color-text-muted); margin-top: 4px; }

.file-preview-list {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 4px;
}
.file-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #fafafa;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
  color: var(--color-text-secondary);
}
.file-preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  transition: background var(--transition-base);
}
.file-preview-item:last-child { border-bottom: none; }
.file-preview-item:hover { background: #f7f8fa; }

.file-type-icon { font-size: 18px; flex-shrink: 0; }
.icon-pdf    { color: #ff4d4f; }
.icon-office { color: #faad14; }
.icon-image  { color: #52c41a; }
.icon-text   { color: var(--color-primary); }

.file-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.file-name {
  font-size: 13px; color: var(--color-text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.file-size { font-size: 11px; color: var(--color-text-muted); }
.modality-tag { flex-shrink: 0; }
.file-remove { flex-shrink: 0; opacity: 0; transition: opacity var(--transition-base); }
.file-preview-item:hover .file-remove { opacity: 1; }

.ingest-right { display: flex; flex-direction: column; gap: 12px; }

.success-item {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; padding: 3px 0;
}
.success-item span { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.doc-list-card { padding: 16px 20px; }
.doc-list-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}
.doc-list-title { font-weight: 500; font-size: 14px; }

.docs-loading, .docs-empty {
  text-align: center; padding: 24px;
  color: var(--color-text-muted); font-size: 13px;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}

.doc-items { display: flex; flex-direction: column; gap: 10px; max-height: 500px; overflow-y: auto; }

.doc-item {
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: #fafafa;
}
.doc-item-main {
  display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
}
.doc-icon { font-size: 15px; flex-shrink: 0; }
.doc-title {
  font-size: 13px; font-weight: 500; color: var(--color-text-primary);
  flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.doc-tags { display: flex; gap: 4px; flex-shrink: 0; flex-wrap: wrap; }

.doc-error {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: #f56c6c; padding: 2px 0 2px 23px;
}

.doc-meta { font-size: 11px; color: var(--color-text-muted); padding-left: 23px; }

.doc-actions {
  display: flex; gap: 8px; padding-top: 4px; padding-left: 20px;
}

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

@media (max-width: 900px) { .ingest-layout { grid-template-columns: 1fr; } }
</style>
