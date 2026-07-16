<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">公众号爆款文案</div>
      <div class="page-desc">生成适合微信公众号的推文标题、导语和正文结构</div>
    </div>
    <div class="promo-layout">
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入信息</div>
        <div class="io-panel-body">
          <el-form :model="form" label-position="top">
            <el-form-item label="文章主题" required>
              <el-input v-model="form.subject" placeholder="例：秋季黄山游全攻略" />
            </el-form-item>
            <el-form-item label="文章类型">
              <el-select v-model="form.type" style="width:100%">
                <el-option label="活动推广" value="event" />
                <el-option label="旅游攻略" value="guide" />
                <el-option label="文化故事" value="story" />
                <el-option label="行业资讯" value="news" />
              </el-select>
            </el-form-item>
            <el-form-item label="文章长度">
              <el-radio-group v-model="form.length">
                <el-radio-button label="短文（800字）" /><el-radio-button label="中文（1500字）" /><el-radio-button label="长文（3000字）" />
              </el-radio-group>
            </el-form-item>
            <el-button type="primary" :loading="loading" @click="generate" style="width:100%" :disabled="!form.subject">
              <el-icon><MagicStick /></el-icon>生成推文
            </el-button>
          </el-form>
        </div>
      </div>
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><ChatLineRound /></el-icon>公众号推文</div>
        <div class="io-panel-body">
          <div v-if="!result && !loading" class="wip-placeholder">
            <el-icon><ChatLineRound /></el-icon><span>填写信息后生成推文</span>
          </div>
          <div v-else-if="loading" class="wip-placeholder">
            <el-icon class="spin"><Loading /></el-icon><span>生成中...</span>
          </div>
          <div v-else class="wechat-preview md-output" v-html="renderedResult" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
const form = ref({ subject: '', type: 'guide', length: '中文（1500字）' })
const loading = ref(false)
const result = ref('')
const renderedResult = computed(() => result.value ? marked.parse(result.value) : '')
async function generate() {
  loading.value = true; result.value = ''
  await new Promise(r => setTimeout(r, 700))
  result.value = `# ${form.value.subject}\n\n> 公众号推文生成功能接入中\n\n**导语：** 这里即将呈现一篇精心撰写的公众号推文，主题为"${form.value.subject}"，目标长度 ${form.value.length}。\n\n## 正文（示例结构）\n\n### 一、开篇引入\n吸引读者注意力的开场段落...\n\n### 二、主体内容\n详细介绍活动/景区/产品的核心内容...\n\n### 三、行动引导\n引导读者转发、收藏或前往体验...`
  loading.value = false
}
</script>

<style scoped>
.promo-layout { display: grid; grid-template-columns: 380px 1fr; gap: 16px; min-height: 500px; }
.io-panel { display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.io-panel-header { padding: 12px 20px; border-bottom: 1px solid var(--color-border); font-weight: 500; font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; background: #fafafa; flex-shrink: 0; }
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }
.wechat-preview { background: #fff; padding: 8px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .promo-layout { grid-template-columns: 1fr; } }
</style>
