<template>
  <aside class="sidebar" :class="{ collapsed: collapsed }">
    <!-- Logo 区域 -->
    <div class="sidebar-logo">
      <span class="logo-icon">🏔️</span>
      <span class="logo-text">AI文旅工作台</span>
    </div>

    <!-- 折叠按钮 -->
    <div class="sidebar-toggle" @click="toggle" :title="collapsed ? '展开菜单' : '收起菜单'">
      <el-icon><ArrowRight v-if="collapsed" /><ArrowLeft v-else /></el-icon>
    </div>

    <!-- 菜单 -->
    <el-scrollbar class="sidebar-scroll">
      <el-menu
        :default-active="route.path"
        router
        :collapse="collapsed"
        :collapse-transition="false"
        background-color="transparent"
        text-color="#40414f"
        active-text-color="#0d0d0d"
        class="sidebar-menu"
      >
        <!-- AI 问答（一级直接路由） -->
        <el-menu-item index="/ai-chat">
          <el-icon><ChatDotSquare /></el-icon>
          <template #title>AI问答</template>
        </el-menu-item>

        <!-- 设计策划方案 -->
        <el-sub-menu index="planning">
          <template #title>
            <el-icon><EditPen /></el-icon>
            <span>设计策划方案</span>
          </template>
          <el-menu-item index="/planning/search"><el-icon><Search /></el-icon>资料查询</el-menu-item>
          <el-menu-item index="/planning/outline"><el-icon><List /></el-icon>策划大纲</el-menu-item>
          <el-menu-item index="/planning/full-text"><el-icon><Document /></el-icon>策划全稿</el-menu-item>
          <el-menu-item index="/planning/ppt"><el-icon><Paperclip /></el-icon>策划方案（PPT）</el-menu-item>
          <el-menu-item index="/planning/image"><el-icon><Picture /></el-icon>图片方案生成</el-menu-item>
        </el-sub-menu>

        <!-- 对外宣发 -->
        <el-sub-menu index="promotion">
          <template #title>
            <el-icon><Promotion /></el-icon>
            <span>对外宣发</span>
          </template>
          <el-menu-item index="/promotion/xiaohongshu"><el-icon><StarFilled /></el-icon>小红书爆款文案</el-menu-item>
          <el-menu-item index="/promotion/douyin"><el-icon><VideoPlay /></el-icon>抖音爆款文案</el-menu-item>
          <el-menu-item index="/promotion/wechat"><el-icon><ChatLineRound /></el-icon>公众号爆款文案</el-menu-item>
          <el-menu-item index="/promotion/video"><el-icon><Film /></el-icon>视频生成</el-menu-item>
        </el-sub-menu>

        <!-- 文创IP -->
        <el-sub-menu index="ip">
          <template #title>
            <el-icon><MagicStick /></el-icon>
            <span>文创IP</span>
          </template>
          <el-menu-item index="/ip/design"><el-icon><Brush /></el-icon>文创设计</el-menu-item>
          <el-menu-item index="/ip/products"><el-icon><Box /></el-icon>衍生品设计</el-menu-item>
        </el-sub-menu>

        <!-- 资源库 -->
        <el-sub-menu index="resources">
          <template #title>
            <el-icon><FolderOpened /></el-icon>
            <span>资源库</span>
          </template>
          <el-menu-item index="/resources/categories"><el-icon><Menu /></el-icon>资源分类</el-menu-item>
          <el-menu-item index="/resources/browse"><el-icon><Files /></el-icon>资料展示</el-menu-item>
          <el-menu-item index="/resources/ingest"><el-icon><Upload /></el-icon>资源库录入</el-menu-item>
          <el-menu-item index="/resources/reports"><el-icon><DataAnalysis /></el-icon>数据报告</el-menu-item>
        </el-sub-menu>

        <!-- 其他 -->
        <el-sub-menu index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>其他</span>
          </template>
          <el-menu-item index="/system/audit"><el-icon><Tickets /></el-icon>审计</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-scrollbar>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app.js'
import { storeToRefs } from 'pinia'

const route = useRoute()
const appStore = useAppStore()
const { sidebarCollapsed: collapsed } = storeToRefs(appStore)

function toggle() {
  appStore.toggleSidebar()
}
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  background: var(--color-sidebar-bg);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: 100vh;
  overflow: hidden;
  transition: width var(--transition-base);
  position: relative;
  z-index: 100;
  border-right: 1px solid var(--color-sidebar-border);
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

/* Logo */
.sidebar-logo {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 56px 0 20px;
  border-bottom: 1px solid var(--color-sidebar-border);
  overflow: hidden;
  flex-shrink: 0;
  white-space: nowrap;
}

.logo-icon { font-size: 22px; flex-shrink: 0; }

.logo-text {
  font-size: 15px;
  font-weight: 700;
  color: #3a2828;
  letter-spacing: 0.5px;
  white-space: nowrap;
  transition: opacity var(--transition-base);
}

.sidebar.collapsed .logo-text {
  opacity: 0;
  width: 0;
}

.sidebar.collapsed .logo-icon {
  opacity: 0;
}

/* 折叠按钮 */
.sidebar-toggle {
  position: absolute;
  right: 12px;
  top: calc(var(--topbar-height) / 2);
  transform: translateY(-50%);
  width: 34px;
  height: 34px;
  border: 1px solid var(--color-sidebar-border);
  border-radius: 8px;
  background: #ffffff;
  color: #40414f;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: background var(--transition-base), border-color var(--transition-base);
}

.sidebar.collapsed .sidebar-toggle {
  right: 15px;
}

.sidebar-toggle:hover {
  background: #ececec;
  border-color: #d5d5d5;
}

.sidebar-toggle .el-icon {
  font-size: 18px;
}

/* 滚动区域 */
.sidebar-scroll {
  flex: 1;
}

/* 菜单覆盖 */
.sidebar-menu {
  border: none !important;
  padding: 8px;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: #ececec;
  --el-menu-active-bg-color: var(--color-sidebar-active);
  --el-menu-item-height: 42px;
  --el-menu-sub-item-height: 38px;
}

/* 一级菜单项 / 子菜单标题：圆角 pill 风格 */
:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  border-radius: 8px;
  margin: 2px 0;
}

:deep(.el-menu-item.is-active) {
  background-color: var(--color-sidebar-active) !important;
  border-radius: 8px;
  font-weight: 600;
}

:deep(.el-sub-menu__title:hover),
:deep(.el-menu-item:hover) {
  background: #ececec !important;
}

:deep(.el-sub-menu__title) {
  color: #40414f !important;
}

:deep(.el-sub-menu.is-opened > .el-sub-menu__title) {
  color: #0d0d0d !important;
}

/* 展开的子菜单：略深于侧栏底色，区分层级 */
:deep(.el-menu--inline) {
  background: #f0f0f0 !important;
  border-radius: 8px;
  margin: 2px 0;
}

:deep(.el-menu--inline .el-menu-item) {
  border-radius: 6px;
}
</style>
