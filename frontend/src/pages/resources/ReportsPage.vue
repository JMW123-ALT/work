<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">数据报告</div>
      <div class="page-desc">定制化数据分析报告，面向企业和政府服务</div>
    </div>

    <div class="reports-grid">
      <div class="report-type-card work-card" v-for="type in reportTypes" :key="type.key">
        <div class="report-type-header">
          <el-icon :size="28" class="report-icon"><component :is="type.icon" /></el-icon>
          <div>
            <div class="report-type-title">{{ type.title }}</div>
            <div class="report-type-desc">{{ type.desc }}</div>
          </div>
        </div>
        <el-divider style="margin:12px 0" />
        <el-form label-position="top" size="small">
          <el-form-item label="报告周期">
            <el-radio-group v-model="type.period">
              <el-radio-button label="月报" /><el-radio-button label="季报" /><el-radio-button label="年报" />
            </el-radio-group>
          </el-form-item>
          <el-form-item label="关注维度">
            <el-checkbox-group v-model="type.dimensions">
              <el-checkbox v-for="d in type.availableDimensions" :key="d" :label="d" />
            </el-checkbox-group>
          </el-form-item>
          <el-button type="primary" disabled size="small" style="width:100%">生成报告（接入中）</el-button>
        </el-form>
      </div>
    </div>

    <el-alert
      title="数据报告生成功能接入中，后续将连接文旅数据库，支持自动拉取游客量、消费数据、景区评分等指标，生成专业分析报告。"
      type="info"
      show-icon
      :closable="false"
      style="margin-top:16px"
    />
  </div>
</template>

<script setup>
import { reactive } from 'vue'

const reportTypes = reactive([
  {
    key: 'enterprise',
    title: '企业报告',
    icon: 'OfficeBuilding',
    desc: '面向景区、文旅企业的运营数据分析',
    period: '月报',
    dimensions: ['游客量', '收入分析'],
    availableDimensions: ['游客量', '收入分析', '转化率', '评价分析', '竞品对比'],
  },
  {
    key: 'government',
    title: '政府报告',
    icon: 'Postcard',
    desc: '面向文旅主管部门的综合发展报告',
    period: '季报',
    dimensions: ['区域文旅概览', '政策落地评估'],
    availableDimensions: ['区域文旅概览', '政策落地评估', '重点项目进展', '人才就业', '经济贡献'],
  },
])
</script>

<style scoped>
.reports-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.report-type-card { padding: 20px 24px; }
.report-type-header { display: flex; align-items: flex-start; gap: 14px; }
.report-icon { color: var(--color-primary); flex-shrink: 0; margin-top: 2px; }
.report-type-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.report-type-desc { font-size: 13px; color: var(--color-text-muted); }
@media (max-width: 900px) { .reports-grid { grid-template-columns: 1fr; } }
</style>
