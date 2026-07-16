<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">策划大纲</div>
      <div class="page-desc">输入主题、目标与受众，AI 生成结构化策划大纲</div>
    </div>
    <div class="io-layout">
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入信息</div>
        <div class="io-panel-body">
          <el-form :model="form" label-position="top">
            <el-form-item label="策划主题" required>
              <el-input v-model="form.theme" placeholder="例：黄山秋季文旅节活动策划" />
            </el-form-item>
            <el-form-item label="策划目标">
              <el-input v-model="form.goal" placeholder="例：提升景区冬季客流量 30%" />
            </el-form-item>
            <el-form-item label="目标受众">
              <el-input v-model="form.audience" placeholder="例：25-40 岁家庭亲子游客" />
            </el-form-item>
            <el-form-item label="资料上下文（可选，来自资料查询页）">
              <el-input v-model="form.context" type="textarea" :autosize="{ minRows: 3 }" placeholder="粘贴参考资料..." />
            </el-form-item>
            <el-button type="primary" :loading="loading" @click="generate" style="width:100%" :disabled="!form.theme">
              <el-icon><MagicStick /></el-icon>生成大纲
            </el-button>
          </el-form>
        </div>
      </div>
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><List /></el-icon>生成的大纲</div>
        <div class="io-panel-body">
          <div v-if="!result && !loading" class="wip-placeholder">
            <el-icon><List /></el-icon><span>填写左侧信息后生成大纲</span>
          </div>
          <div v-else-if="loading" class="wip-placeholder">
            <el-icon class="spin"><Loading /></el-icon><span>生成中...</span>
          </div>
          <div v-else class="md-output" v-html="renderedResult" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
const form = ref({ theme: '', goal: '', audience: '', context: '' })
const loading = ref(false)
const result = ref('')
const renderedResult = computed(() => result.value ? marked.parse(result.value) : '')

async function generate() {
  loading.value = true
  result.value = ''
  await new Promise(r => setTimeout(r, 600))
  result.value = `# ${form.value.theme} 策划大纲\n\n> 功能接入中，下方为示例结构\n\n## 一、项目概述\n- 主题：${form.value.theme}\n- 目标：${form.value.goal || '待填写'}\n- 受众：${form.value.audience || '待填写'}\n\n## 二、核心策略\n1. 主题定位\n2. 内容规划\n3. 渠道推广\n\n## 三、执行计划\n- 筹备阶段\n- 执行阶段\n- 收尾阶段\n\n## 四、预算概览\n待接入真实生成接口`
  loading.value = false
}
</script>

<style scoped>
.io-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; min-height: 500px; }
.io-panel { display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.io-panel-header { padding: 12px 20px; border-bottom: 1px solid var(--color-border); font-weight: 500; font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; background: #fafafa; flex-shrink: 0; }
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .io-layout { grid-template-columns: 1fr; } }
</style>
