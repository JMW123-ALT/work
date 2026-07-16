<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">视频生成</div>
      <div class="page-desc">生成视频脚本、分镜说明和旁白文案</div>
    </div>
    <div class="work-card" style="padding:28px 32px">
      <div class="video-intro">
        <el-icon class="video-icon"><Film /></el-icon>
        <div>
          <div class="video-title">视频内容生成</div>
          <div class="video-desc">自动生成视频脚本、分镜描述和配音文案</div>
        </div>
      </div>
      <el-divider />
      <el-form :model="form" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="视频主题">
              <el-input v-model="form.subject" placeholder="例：黄山四季主题宣传片" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="视频类型">
              <el-select v-model="form.type" style="width:100%">
                <el-option label="宣传片" value="promo" />
                <el-option label="vlog 脚本" value="vlog" />
                <el-option label="短视频口播" value="talk" />
                <el-option label="纪录片旁白" value="doc" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="时长">
              <el-select v-model="form.duration" style="width:100%">
                <el-option label="30秒" value="30s" />
                <el-option label="1分钟" value="1min" />
                <el-option label="3分钟" value="3min" />
                <el-option label="5分钟" value="5min" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" disabled size="large">
            <el-icon><Film /></el-icon>生成视频脚本（接口接入中）
          </el-button>
          <el-tag type="warning" style="margin-left:12px">待接入视频脚本生成服务</el-tag>
        </el-form-item>
      </el-form>
      <el-alert title="视频脚本生成功能接入中，后续将支持自动分镜、配音文案、画面描述等。" type="info" show-icon :closable="false" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const form = ref({ subject: '', type: 'promo', duration: '1min' })
</script>

<style scoped>
.video-intro { display: flex; align-items: center; gap: 16px; }
.video-icon { font-size: 40px; color: var(--color-primary); }
.video-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.video-desc { font-size: 13px; color: var(--color-text-muted); }
</style>
