<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">资源分类</div>
      <div class="page-desc">查看资源库的分类体系，包含策划方案、政策、数据等大类</div>
    </div>

    <el-alert
      v-if="!backendHealthy"
      title="后端服务离线，分类数据无法加载"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom:16px"
    />

    <div class="work-card" v-if="loading">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="!categories.length" class="empty-card work-card">
      <el-empty description="暂无分类数据，请检查后端连接">
        <el-button type="primary" plain @click="load">重新加载</el-button>
      </el-empty>
    </div>

    <template v-else>
      <div class="categories-grid">
        <div
          v-for="cat in rootCategories"
          :key="cat.id"
          class="category-card work-card"
        >
          <div class="cat-header">
            <el-icon class="cat-icon"><FolderOpened /></el-icon>
            <span class="cat-name">{{ cat.label || cat.name }}</span>
            <el-tag size="small" type="info" v-if="cat.count !== undefined">{{ cat.count }} 条</el-tag>
          </div>
          <div class="cat-desc" v-if="cat.description">{{ cat.description }}</div>
          <div class="cat-children" v-if="childrenOf(cat.id).length">
            <div
              v-for="child in childrenOf(cat.id)"
              :key="child.id"
              class="cat-child"
            >
              <el-icon><Document /></el-icon>
              <span>{{ child.label || child.name }}</span>
              <el-tag v-if="child.count" size="small" type="info" style="margin-left:auto">{{ child.count }}</el-tag>
            </div>
          </div>
          <div class="cat-meta" v-if="cat.id">
            <span class="cat-id">ID: {{ cat.id }}</span>
          </div>
        </div>
      </div>

      <!-- 完整扁平列表 -->
      <div class="work-card" style="margin-top:16px">
        <div class="doc-list-header" style="margin-bottom:12px">
          <span style="font-weight:500">全部分类（{{ categories.length }} 项）</span>
          <el-button link size="small" @click="load"><el-icon><Refresh /></el-icon>刷新</el-button>
        </div>
        <el-table :data="categories" border stripe size="small">
          <el-table-column prop="id" label="分类 ID" width="160" />
          <el-table-column label="名称" min-width="120">
            <template #default="{ row }">{{ row.label || row.name || '-' }}</template>
          </el-table-column>
          <el-table-column label="父分类" width="140">
            <template #default="{ row }">
              <span v-if="row.parent_id">{{ labelOf(row.parent_id) }}</span>
              <el-tag v-else size="small" type="success">一级分类</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="描述" min-width="200">
            <template #default="{ row }">{{ row.description || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { getCategories } from '@/api/resources.js'
import { useAppStore } from '@/stores/app.js'
import { useResourcesStore } from '@/stores/resources.js'

const appStore = useAppStore()
const resourcesStore = useResourcesStore()
const { backendHealthy } = storeToRefs(appStore)

const loading = ref(false)
const categories = ref([])

const rootCategories = computed(() => categories.value.filter(c => !c.parent_id))

function childrenOf(parentId) {
  return categories.value.filter(c => c.parent_id === parentId)
}

function labelOf(id) {
  const found = categories.value.find(c => c.id === id)
  return found ? (found.label || found.name || id) : id
}

async function load() {
  loading.value = true
  try {
    const data = await getCategories()
    categories.value = data.items || []
    resourcesStore.categories = categories.value
  } catch {
    categories.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.category-card { padding: 16px 20px; }

.cat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.cat-icon { color: var(--color-primary); font-size: 18px; }
.cat-name { font-size: 15px; font-weight: 600; flex: 1; }

.cat-desc { font-size: 13px; color: var(--color-text-muted); margin-bottom: 10px; }

.cat-children { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; }

.cat-child {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f7f8fa;
  color: var(--color-text-secondary);
}
.cat-child .el-icon { color: #aaa; font-size: 12px; }

.cat-meta { font-size: 11px; color: #ccc; }
.cat-id { font-family: monospace; }

.empty-card { padding: 48px; }
</style>
