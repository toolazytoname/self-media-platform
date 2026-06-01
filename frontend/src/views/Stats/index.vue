<template>
  <div class="stats-page">
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon">📝</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.topics_total }}</div>
            <div class="stat-label">选题总数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon">🖼️</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.materials_total }}</div>
            <div class="stat-label">素材总数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon">📋</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.content_total }}</div>
            <div class="stat-label">内容总数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card highlight">
          <div class="stat-icon">⏳</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.review_pending }}</div>
            <div class="stat-label">待审核</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>📊</span>
              <span>平台分布</span>
            </div>
          </template>
          <div class="platform-list">
            <div v-for="(item, index) in platformStats" :key="index" class="platform-item">
              <div class="platform-name">{{ item.name }}</div>
              <div class="platform-bar">
                <div class="bar-fill" :style="{ width: item.percent + '%' }"></div>
              </div>
              <div class="platform-count">{{ item.count }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>📈</span>
              <span>发布趋势</span>
            </div>
          </template>
          <div class="chart-placeholder">
            <div class="placeholder-content">
              <span>📊</span>
              <p>图表加载中...</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const stats = ref({
  topics_total: 0,
  materials_total: 0,
  content_total: 0,
  review_pending: 0
})

const platformStats = ref([
  { name: '抖音', count: 12, percent: 80 },
  { name: '小红书', count: 15, percent: 100 },
  { name: 'B站', count: 8, percent: 53 },
  { name: '头条号', count: 6, percent: 40 }
])

onMounted(async () => {
  try {
    const res = await axios.get('/api/cms/stats')
    stats.value = res.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
})
</script>

<style scoped>
.stats-page {
  padding: 0;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.3);
}

.stat-card.highlight {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(26, 26, 46, 0.6) 100%);
  border-color: rgba(0, 212, 255, 0.3);
}

.stat-icon {
  font-size: 36px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #a0a0b0;
  margin-top: 8px;
}

.charts-row {
  margin-bottom: 24px;
}

.chart-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.platform-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.platform-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.platform-name {
  width: 80px;
  font-size: 14px;
  color: #e0e0e0;
}

.platform-bar {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00d4ff 0%, #00a8cc 100%);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.platform-count {
  width: 40px;
  text-align: right;
  font-size: 14px;
  color: #00d4ff;
  font-weight: 600;
}

.chart-placeholder {
  height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
}

.placeholder-content {
  text-align: center;
  color: #666;
}

.placeholder-content span {
  font-size: 48px;
}

.placeholder-content p {
  margin-top: 12px;
}
</style>