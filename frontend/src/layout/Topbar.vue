<template>
  <header class="topbar">
    <div class="topbar-left">
      <span class="topbar-title">AI 文旅工作台</span>
      <span class="topbar-breadcrumb">{{ currentTitle }}</span>
    </div>

    <div class="topbar-right">
      <!-- 用户类型 -->
      <el-select
        :model-value="appStore.currentUserType"
        @update:model-value="appStore.setUserType"
        size="small"
        style="width: 110px"
        placeholder="用户类型"
      >
        <el-option label="访客" value="visitor" />
        <el-option label="内部用户" value="internal" />
        <el-option label="管理员" value="admin" />
      </el-select>

      <!-- 后端连接状态 -->
      <div class="health-badge" :title="healthTitle">
        <span
          class="status-dot"
          :class="{
            online: appStore.backendHealthy === true,
            offline: appStore.backendHealthy === false,
            checking: appStore.backendHealthy === null,
          }"
        />
        <span class="health-text">{{ healthTitle }}</span>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app.js'

const route = useRoute()
const appStore = useAppStore()

const currentTitle = computed(() => route.meta?.title || '')

const healthTitle = computed(() => {
  if (appStore.backendHealthy === null) return '检测中'
  return appStore.backendHealthy ? '后端在线' : '后端离线'
})
</script>

<style scoped>
.topbar {
  height: var(--topbar-height);
  background: var(--color-card-bg);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  z-index: 50;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.topbar-breadcrumb {
  font-size: 13px;
  color: var(--color-text-muted);
  padding-left: 12px;
  border-left: 1px solid var(--color-border);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.health-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  background: #f5f5f5;
  cursor: default;
}

.health-text {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}
</style>
