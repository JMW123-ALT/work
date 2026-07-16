<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">图片方案生成</div>
      <div class="page-desc">提示词生成、文生图、图生图三种模式</div>
    </div>

    <el-tabs v-model="activeTab" class="image-tabs">

      <!-- Tab 1: 提示词生成 -->
      <el-tab-pane label="提示词生成" name="prompt">
        <div class="io-layout">
          <div class="io-panel work-card">
            <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入主题</div>
            <div class="io-panel-body">
              <el-form label-position="top">
                <el-form-item label="画面主题">
                  <el-input v-model="promptForm.theme" placeholder="例：黄山云海日出，意境空灵" />
                </el-form-item>
                <el-form-item label="风格">
                  <el-radio-group v-model="promptForm.style">
                    <el-radio-button label="写实摄影" />
                    <el-radio-button label="国风插画" />
                    <el-radio-button label="水墨" />
                    <el-radio-button label="3D渲染" />
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="比例">
                  <el-radio-group v-model="promptForm.ratio">
                    <el-radio-button label="16:9" />
                    <el-radio-button label="1:1" />
                    <el-radio-button label="9:16" />
                    <el-radio-button label="4:3" />
                  </el-radio-group>
                </el-form-item>
                <el-button type="primary" :loading="promptLoading" @click="genPrompt" style="width:100%">
                  生成提示词
                </el-button>
              </el-form>
            </div>
          </div>
          <div class="io-panel work-card">
            <div class="io-panel-header"><el-icon><Document /></el-icon>生成的提示词</div>
            <div class="io-panel-body">
              <div v-if="!generatedPrompt" class="wip-placeholder">
                <el-icon><Picture /></el-icon><span>填写主题后生成</span>
              </div>
              <div v-else>
                <el-input v-model="generatedPrompt" type="textarea" :autosize="{ minRows: 6 }" />
                <el-button style="margin-top:10px" plain @click="copyPrompt">
                  <el-icon><CopyDocument /></el-icon>复制提示词
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 文生图 -->
      <el-tab-pane label="文生图" name="text2img">
        <div class="io-layout">
          <div class="io-panel work-card">
            <div class="io-panel-header"><el-icon><EditPen /></el-icon>输入提示词</div>
            <div class="io-panel-body">
              <el-form label-position="top">
                <el-form-item label="图片提示词（中/英文均可）" required>
                  <el-input v-model="t2iForm.prompt" type="textarea" :autosize="{ minRows: 4 }" placeholder="描述你想要的画面..." />
                </el-form-item>
                <el-form-item label="负面提示词（可选）">
                  <el-input v-model="t2iForm.negative" type="textarea" :autosize="{ minRows: 2 }" placeholder="不希望出现的内容" />
                </el-form-item>
                <el-button type="primary" disabled style="width:100%">生成图片（接口接入中）</el-button>
              </el-form>
            </div>
          </div>
          <div class="io-panel work-card">
            <div class="io-panel-header"><el-icon><Picture /></el-icon>图片预览</div>
            <div class="io-panel-body">
              <div class="wip-placeholder">
                <el-icon><Picture /></el-icon>
                <span>文生图功能接入中</span>
                <el-tag type="info">待接入 Stable Diffusion / DALL-E</el-tag>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 图生图 -->
      <el-tab-pane label="图生图" name="img2img">
        <div class="io-layout">
          <div class="io-panel work-card">
            <div class="io-panel-header"><el-icon><EditPen /></el-icon>参考图 + 提示词</div>
            <div class="io-panel-body">
              <el-form label-position="top">
                <el-form-item label="上传参考图">
                  <el-upload drag accept="image/*" :auto-upload="false" v-model:file-list="i2iFiles">
                    <el-icon><UploadFilled /></el-icon>
                    <div>拖拽或点击上传参考图</div>
                  </el-upload>
                </el-form-item>
                <el-form-item label="修改描述">
                  <el-input v-model="i2iForm.prompt" type="textarea" :autosize="{ minRows: 3 }" placeholder="描述对图片的修改要求..." />
                </el-form-item>
                <el-form-item label="参考强度">
                  <el-slider v-model="i2iForm.strength" :min="0" :max="1" :step="0.05" />
                </el-form-item>
                <el-button type="primary" disabled style="width:100%">生成图片（接口接入中）</el-button>
              </el-form>
            </div>
          </div>
          <div class="io-panel work-card">
            <div class="io-panel-header"><el-icon><Picture /></el-icon>生成结果</div>
            <div class="io-panel-body">
              <div class="wip-placeholder">
                <el-icon><Picture /></el-icon>
                <span>图生图功能接入中</span>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('prompt')
const promptLoading = ref(false)
const generatedPrompt = ref('')

const promptForm = ref({ theme: '', style: '写实摄影', ratio: '16:9' })
const t2iForm = ref({ prompt: '', negative: '' })
const i2iForm = ref({ prompt: '', strength: 0.75 })
const i2iFiles = ref([])

async function genPrompt() {
  if (!promptForm.value.theme.trim()) return
  promptLoading.value = true
  await new Promise(r => setTimeout(r, 800)) // 占位，后续接真实接口
  generatedPrompt.value = `${promptForm.value.theme}，${promptForm.value.style}风格，${promptForm.value.ratio}比例，高清细节，专业摄影，cinematic lighting, masterpiece, best quality`
  promptLoading.value = false
}

function copyPrompt() {
  navigator.clipboard.writeText(generatedPrompt.value)
  ElMessage.success('已复制到剪贴板')
}
</script>

<style scoped>
.image-tabs { margin-top: -8px; }
.io-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
  min-height: 400px;
}
.io-panel { display: flex; flex-direction: column; overflow: hidden; padding: 0; }
.io-panel-header {
  padding: 12px 20px;
  border-bottom: 1px solid var(--color-border);
  font-weight: 500;
  font-size: 13px;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fafafa;
  flex-shrink: 0;
}
.io-panel-body { flex: 1; padding: 16px 20px; overflow-y: auto; }
@media (max-width: 900px) { .io-layout { grid-template-columns: 1fr; } }
</style>
