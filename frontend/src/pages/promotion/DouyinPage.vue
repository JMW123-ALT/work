<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">抖音爆款文案</div>
      <div class="page-desc">生成适合抖音短视频的开场白、口播脚本和评论引导文案</div>
    </div>
    <div class="promo-layout">
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入信息</div>
        <div class="io-panel-body">
          <el-form :model="form" label-position="top">
            <el-form-item label="视频主题/景区/活动" required>
              <el-input v-model="form.subject" placeholder="例：西湖夜游体验vlog" />
            </el-form-item>
            <el-form-item label="文案类型">
              <el-radio-group v-model="form.type">
                <el-radio-button label="开场白" /><el-radio-button label="口播脚本" /><el-radio-button label="评论引导" />
              </el-radio-group>
            </el-form-item>
            <el-form-item label="视频时长">
              <el-radio-group v-model="form.duration">
                <el-radio-button label="15s" /><el-radio-button label="30s" /><el-radio-button label="1min" /><el-radio-button label="3min+" />
              </el-radio-group>
            </el-form-item>
            <el-form-item label="风格">
              <el-radio-group v-model="form.style">
                <el-radio-button label="搞笑反差" /><el-radio-button label="情绪共鸣" /><el-radio-button label="干货攻略" />
              </el-radio-group>
            </el-form-item>
            <el-button type="primary" :loading="loading" @click="generate" style="width:100%" :disabled="!form.subject">
              <el-icon><MagicStick /></el-icon>生成文案
            </el-button>
          </el-form>
        </div>
      </div>
      <div class="io-panel work-card">
        <div class="io-panel-header">
          <el-icon><VideoPlay /></el-icon>抖音文案
          <div style="flex:1" />
          <el-button v-if="result" link size="small" @click="copy"><el-icon><CopyDocument /></el-icon>复制</el-button>
        </div>
        <div class="io-panel-body">
          <div v-if="!result && !loading" class="wip-placeholder">
            <el-icon><VideoPlay /></el-icon><span>填写信息后生成</span>
          </div>
          <div v-else-if="loading" class="wip-placeholder">
            <el-icon class="spin"><Loading /></el-icon><span>生成中...</span>
          </div>
          <div v-else class="douyin-preview">
            <pre class="douyin-text">{{ result }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
const form = ref({ subject: '', type: '开场白', duration: '30s', style: '情绪共鸣' })
const loading = ref(false)
const result = ref('')
async function generate() {
  loading.value = true; result.value = ''
  await new Promise(r => setTimeout(r, 700))
  result.value = `【${form.value.type}·${form.value.duration}·${form.value.style}】\n\n"${form.value.subject}"\n\n---\n（待接入真实生成接口）\n\n示例开场白：\n"等等，你知道${form.value.subject}有多美吗？\n我拍了 300 张，每张都想设成屏保！"\n\n---\n话题标签：\n#${form.value.subject} #文旅打卡 #抖音推荐`
  loading.value = false
}
function copy() { navigator.clipboard.writeText(result.value); ElMessage.success('已复制') }
</script>

<style scoped>
.promo-layout { display: grid; grid-template-columns: 380px 1fr; gap: 16px; min-height: 500px; }
.io-panel { display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.io-panel-header { padding: 12px 20px; border-bottom: 1px solid var(--color-border); font-weight: 500; font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; background: #fafafa; flex-shrink: 0; }
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }
.douyin-preview { background: #0a0a0a; border-radius: 12px; padding: 20px; }
.douyin-text { color: #fff; font-size: 14px; line-height: 1.8; white-space: pre-wrap; font-family: inherit; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .promo-layout { grid-template-columns: 1fr; } }
</style>
