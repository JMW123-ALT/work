<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">策划全稿</div>
      <div class="page-desc">基于大纲和资料上下文，生成完整策划方案文字稿</div>
    </div>
    <div class="io-layout">
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入大纲 / 要求</div>
        <div class="io-panel-body">
          <el-form label-position="top">
            <el-form-item label="策划主题" required>
              <el-input v-model="form.theme" placeholder="策划方案主题" />
            </el-form-item>
            <el-form-item label="大纲内容">
              <el-input v-model="form.outline" type="textarea" :autosize="{ minRows: 5 }" placeholder="粘贴已生成的大纲，或直接输入要求..." />
            </el-form-item>
            <el-form-item label="字数要求">
              <el-radio-group v-model="form.wordCount">
                <el-radio-button label="1000字" /><el-radio-button label="3000字" /><el-radio-button label="5000字" />
              </el-radio-group>
            </el-form-item>
            <el-button type="primary" :loading="loading" @click="generate" style="width:100%" :disabled="!form.theme">
              <el-icon><Document /></el-icon>生成全稿
            </el-button>
          </el-form>
        </div>
      </div>
      <div class="io-panel work-card">
        <div class="io-panel-header">
          <el-icon><Document /></el-icon>策划全稿
          <div style="flex:1" />
          <el-button v-if="result" link size="small" @click="copyResult"><el-icon><CopyDocument /></el-icon>复制</el-button>
        </div>
        <div class="io-panel-body">
          <div v-if="!result && !loading" class="wip-placeholder">
            <el-icon><Document /></el-icon><span>填写主题后生成全稿</span>
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
import { ElMessage } from 'element-plus'
const form = ref({ theme: '', outline: '', wordCount: '3000字' })
const loading = ref(false)
const result = ref('')
const renderedResult = computed(() => result.value ? marked.parse(result.value) : '')
async function generate() {
  loading.value = true; result.value = ''
  await new Promise(r => setTimeout(r, 800))
  result.value = `# ${form.value.theme}\n\n> 策划全稿生成功能接入中，此处为功能框架预览\n\n## 一、项目背景与意义\n\n待接入真实 LLM 生成接口后，此处将输出完整的策划方案全文，预计 ${form.value.wordCount}。\n\n## 二、核心内容策划\n\n内容待生成...\n\n## 三、执行方案\n\n执行方案待生成...`
  loading.value = false
}
function copyResult() {
  navigator.clipboard.writeText(result.value)
  ElMessage.success('已复制')
}
</script>

<style scoped>
.io-layout { display: grid; grid-template-columns: 380px 1fr; gap: 16px; height: calc(100vh - var(--topbar-height) - 100px); }
.io-panel { display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.io-panel-header { padding: 12px 20px; border-bottom: 1px solid var(--color-border); font-weight: 500; font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; background: #fafafa; flex-shrink: 0; }
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .io-layout { grid-template-columns: 1fr; height: auto; } }
</style>
