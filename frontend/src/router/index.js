import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layout/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/ai-chat',
    children: [
      // AI 问答
      { path: '/ai-chat', component: () => import('@/pages/ai/AiChatPage.vue'), meta: { title: 'AI问答' } },

      // 设计策划方案
      { path: '/planning/search',    component: () => import('@/pages/planning/ResourceSearchPage.vue'), meta: { title: '资料查询' } },
      { path: '/planning/outline',   component: () => import('@/pages/planning/OutlinePage.vue'),        meta: { title: '策划大纲' } },
      { path: '/planning/full-text', component: () => import('@/pages/planning/FullTextPage.vue'),       meta: { title: '策划全稿' } },
      { path: '/planning/ppt',       component: () => import('@/pages/planning/PptPage.vue'),            meta: { title: '策划方案（PPT）' } },
      { path: '/planning/image',     component: () => import('@/pages/planning/ImagePlanPage.vue'),      meta: { title: '图片方案生成' } },

      // 对外宣发
      { path: '/promotion/xiaohongshu', component: () => import('@/pages/promotion/XiaohongshuPage.vue'), meta: { title: '小红书爆款文案' } },
      { path: '/promotion/douyin',      component: () => import('@/pages/promotion/DouyinPage.vue'),       meta: { title: '抖音爆款文案' } },
      { path: '/promotion/wechat',      component: () => import('@/pages/promotion/WechatPage.vue'),       meta: { title: '公众号爆款文案' } },
      { path: '/promotion/video',       component: () => import('@/pages/promotion/VideoPage.vue'),        meta: { title: '视频生成' } },

      // 文创IP
      { path: '/ip/design',   component: () => import('@/pages/ip/IpDesignPage.vue'),      meta: { title: '文创设计' } },
      { path: '/ip/products', component: () => import('@/pages/ip/ProductDesignPage.vue'), meta: { title: '衍生品设计' } },

      // 资源库
      { path: '/resources/categories', component: () => import('@/pages/resources/CategoriesPage.vue'), meta: { title: '资源分类' } },
      { path: '/resources/browse',     component: () => import('@/pages/resources/BrowsePage.vue'),     meta: { title: '资料展示' } },
      { path: '/resources/ingest',     component: () => import('@/pages/resources/IngestPage.vue'),     meta: { title: '资源库录入' } },
      { path: '/resources/reports',    component: () => import('@/pages/resources/ReportsPage.vue'),    meta: { title: '数据报告' } },

      // 其他
      { path: '/system/audit', component: () => import('@/pages/system/AuditPage.vue'), meta: { title: '审计' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
