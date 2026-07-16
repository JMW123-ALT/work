<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">衍生品设计</div>
      <div class="page-desc">文创用品、产品设计、工业设计三个方向</div>
    </div>
    <div class="products-grid">
      <div
        v-for="cat in categories"
        :key="cat.key"
        class="product-cat work-card"
        :class="{ active: activeCategory === cat.key }"
        @click="activeCategory = cat.key"
      >
        <div class="cat-icon-wrap"><el-icon :size="32"><component :is="cat.icon" /></el-icon></div>
        <div class="cat-title">{{ cat.label }}</div>
        <div class="cat-desc">{{ cat.desc }}</div>
      </div>
    </div>

    <div class="work-card product-form" v-if="activeCategory">
      <div class="form-section-title">{{ currentCat?.label }} 设计需求</div>
      <el-form :model="form" label-position="top">
        <el-row :gutter="16">
          <el-col :span="16">
            <el-form-item label="设计需求描述" required>
              <el-input
                v-model="form.requirement"
                type="textarea"
                :autosize="{ minRows: 4 }"
                :placeholder="currentCat?.placeholder"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="预算范围">
              <el-select v-model="form.budget" style="width:100%">
                <el-option label="5 元以内" value="lt5" />
                <el-option label="5-20 元" value="5to20" />
                <el-option label="20-100 元" value="20to100" />
                <el-option label="100 元以上" value="gt100" />
              </el-select>
            </el-form-item>
            <el-form-item label="批量数量">
              <el-select v-model="form.quantity" style="width:100%">
                <el-option label="样品（1-10件）" value="sample" />
                <el-option label="小批量（100件）" value="small" />
                <el-option label="批量（1000件+）" value="bulk" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-button type="primary" disabled size="large">
          <el-icon><MagicStick /></el-icon>生成设计方案（接入中）
        </el-button>
        <el-tag type="warning" style="margin-left:12px">待接入设计生成服务</el-tag>
      </el-form>
    </div>

    <div v-else class="work-card">
      <el-empty description="请选择上方设计方向" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const activeCategory = ref('')
const form = ref({ requirement: '', budget: '5to20', quantity: 'small' })

const categories = [
  {
    key: 'cultural',
    label: '文创用品',
    icon: 'Brush',
    desc: '冰箱贴、文具、布袋、伴手礼等',
    placeholder: '例：以黄山迎客松为主体，设计一套适合年轻人的文创笔记本套装，需要体现山水意境...',
  },
  {
    key: 'product',
    label: '产品设计',
    icon: 'Box',
    desc: '包装设计、食品文创、生活用品等',
    placeholder: '例：为景区特产徽州毛豆腐设计一款高端礼盒包装，目标客群为商务送礼，需要体现徽文化...',
  },
  {
    key: 'industrial',
    label: '工业设计',
    icon: 'Setting',
    desc: '装置艺术、展陈设计、硬件产品等',
    placeholder: '例：设计一套可移动的文旅主题展陈装置，用于商场快闪活动，需要适合拍照打卡...',
  },
]

const currentCat = computed(() => categories.find(c => c.key === activeCategory.value))
</script>

<style scoped>
.products-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.product-cat {
  padding: 24px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-base);
  border: 2px solid transparent;
}
.product-cat:hover { border-color: var(--color-primary); transform: translateY(-2px); }
.product-cat.active { border-color: var(--color-primary); background: #e6f4ff; }
.cat-icon-wrap { display: flex; justify-content: center; margin-bottom: 10px; color: var(--color-primary); }
.cat-title { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.cat-desc { font-size: 13px; color: var(--color-text-muted); }
.product-form { padding: 24px; }
.form-section-title { font-size: 15px; font-weight: 600; margin-bottom: 16px; color: var(--color-primary); }
@media (max-width: 900px) { .products-grid { grid-template-columns: 1fr; } }
</style>
