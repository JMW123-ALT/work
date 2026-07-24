<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed }">
    <Sidebar />
    <div class="app-main">
      <Topbar />
      <main class="app-content">
        <router-view v-slot="{ Component, route }">
          <transition name="fade-slide" mode="out-in">
            <keep-alive>
              <component :is="Component" :key="route.name || route.path" />
            </keep-alive>
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '@/stores/app.js'
import Sidebar from './Sidebar.vue'
import Topbar from './Topbar.vue'

const appStore = useAppStore()
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: margin-left var(--transition-base);
}

.app-content {
  flex: 1;
  overflow: hidden;
  background: var(--color-page-bg);
}

/* 路由切换动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
