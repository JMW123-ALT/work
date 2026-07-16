<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">小红书爆款文案</div>
      <div class="page-desc">生成适合小红书平台的种草文案，风格活泼、标题吸睛</div>
    </div>
    <div class="promo-layout">
      <div class="io-panel work-card">
        <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入信息</div>
        <div class="io-panel-body">
          <el-form :model="form" label-position="top">
            <el-form-item label="活动/景区/产品名称" required>
              <el-input v-model="form.subject" placeholder="例：黄山景区秋叶季" />
            </el-form-item>
            <el-form-item label="核心亮点（2-4 条）">
              <el-input v-model="form.highlights" type="textarea" :autosize="{ minRows: 3 }" placeholder="一行一条，例：&#10;云海日出拍出大片&#10;万亩秋叶绝美" />
            </el-form-item>
            <el-form-item label="目标人群">
              <el-checkbox-group v-model="form.audience">
                <el-checkbox label="学生党" /><el-checkbox label="情侣" /><el-checkbox label="家庭亲子" /><el-checkbox label="摄影爱好者" />
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="语气风格">
              <el-radio-group v-model="form.tone">
                <el-radio-button label="活泼种草" /><el-radio-button label="文艺小清新" /><el-radio-button label="攻略干货" />
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
          <el-icon><Document /></el-icon>小红书文案
          <div style="flex:1" />
          <el-button v-if="result" link size="small" @click="copy"><el-icon><CopyDocument /></el-icon>复制</el-button>
        </div>
        <div class="io-panel-body">
          <div v-if="!result && !loading" class="wip-placeholder">
            <el-icon><StarFilled /></el-icon><span>填写信息后生成文案</span>
          </div>
          <div v-else-if="loading" class="wip-placeholder">
            <el-icon class="spin"><Loading /></el-icon><span>生成中...</span>
          </div>
          <div v-else class="result-preview">
            <div class="xhs-preview">
              <div class="xhs-title">{{ resultTitle }}</div>
              <div class="xhs-body">{{ resultBody }}</div>
              <div class="xhs-tags">{{ resultTags }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const form = ref({ subject: '', highlights: '', audience: ['情侣'], tone: '活泼种草' })
const loading = ref(false)
const result = ref('')

const resultTitle = computed(() => result.value.split('\n')[0] || '')
const resultBody = computed(() => result.value.split('\n').slice(1, -2).join('\n') || '')
const resultTags = computed(() => result.value.split('\n').slice(-2).join(' ') || '')

async function generate() {
  loading.value = true; result.value = ''
  await new Promise(r => setTimeout(r, 700))
  result.value = `🍂 ${form.value.subject}｜这辈子必去的秋天打卡地！\n\n姐妹们！我找到秋天最美的地方了！！\n\n${form.value.highlights.split('\n').map((h, i) => `✅ ${h}`).join('\n')}\n\n💡 小贴士：建议早起赶日出，云海不等人~\n\n这里真的太适合拍大片了，每一帧都能直接发！\n\n#${form.value.subject} #秋天打卡 #文旅推荐 #小红书旅行`
  loading.value = false
}

function copy() {
  navigator.clipboard.writeText(result.value)
  ElMessage.success('已复制')
}
</script>

<style scoped>
.promo-layout { display: grid; grid-template-columns: 380px 1fr; gap: 16px; min-height: 500px; }
.io-panel { display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.io-panel-header { padding: 12px 20px; border-bottom: 1px solid var(--color-border); font-weight: 500; font-size: 13px; color: var(--color-text-secondary); display: flex; align-items: center; gap: 6px; background: #fafafa; flex-shrink: 0; }
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }
.xhs-preview { background: #fff7f7; border: 1px solid #ffd6d6; border-radius: 12px; padding: 20px; }
.xhs-title { font-size: 15px; font-weight: 700; color: #ff2442; margin-bottom: 12px; }
.xhs-body { font-size: 14px; color: #333; line-height: 1.8; white-space: pre-wrap; margin-bottom: 12px; }
.xhs-tags { font-size: 13px; color: #ff2442; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 900px) { .promo-layout { grid-template-columns: 1fr; } }
</style>
