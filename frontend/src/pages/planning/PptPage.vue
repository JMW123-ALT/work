<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">策划方案（PPT）</div>
      <div class="page-desc">基于策划内容生成 PPT 演示文稿，预留 Kimi 接口入口</div>
    </div>
    <div class="work-card ppt-card">
      <div class="ppt-intro">
        <el-icon class="ppt-icon"><Paperclip /></el-icon>
        <div>
          <div class="ppt-title">PPT 生成功能</div>
          <div class="ppt-desc">将策划方案一键转化为专业 PPT，支持多种模板风格</div>
        </div>
      </div>
      <el-divider />
      <el-form label-position="top" :model="form">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="策划主题">
              <el-input v-model="form.theme" placeholder="例：景区文旅活动策划方案" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="PPT 模板风格">
              <el-select v-model="form.template" style="width:100%">
                <el-option label="商务蓝（默认）" value="business-blue" />
                <el-option label="文旅自然风" value="nature" />
                <el-option label="简约白" value="minimal" />
                <el-option label="国风" value="chinese" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="方案内容（粘贴全稿文字）">
          <el-input v-model="form.content" type="textarea" :autosize="{ minRows: 6, maxRows: 14 }" placeholder="粘贴策划全稿或大纲，AI 将自动结构化成 PPT..." />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" disabled size="large">
            <el-icon><Paperclip /></el-icon>生成 PPT（Kimi 接口接入中）
          </el-button>
          <el-tag type="warning" style="margin-left:12px">待接入 Kimi / AiPPT 等服务</el-tag>
        </el-form-item>
      </el-form>
      <el-alert title="该功能后续将接入 Kimi PPT 生成 API 或 AiPPT，目前为框架预留。策划内容可先在《策划全稿》页面生成。" type="info" show-icon :closable="false" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const form = ref({ theme: '', template: 'business-blue', content: '' })
</script>

<style scoped>
.ppt-card { padding: 28px 32px; }
.ppt-intro { display: flex; align-items: center; gap: 16px; margin-bottom: 8px; }
.ppt-icon { font-size: 40px; color: var(--color-primary); }
.ppt-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.ppt-desc { font-size: 13px; color: var(--color-text-muted); }
</style>
