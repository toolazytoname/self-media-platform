<template>
  <div class="stats-page">
    <!-- 顶部数据卡 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon">📝</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.content_total }}</div>
            <div class="stat-label">内容总数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon">💡</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.topics_total }}</div>
            <div class="stat-label">选题总数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon">🖼️</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.materials_total }}</div>
            <div class="stat-label">素材总数</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card highlight">
          <div class="stat-icon">⏳</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.review_pending }}</div>
            <div class="stat-label">待审核</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="stats-row-2">
      <el-col :xs="12" :sm="6">
        <div class="stat-card mini">
          <div class="stat-info">
            <div class="stat-value-sm">{{ stats.content_draft }}</div>
            <div class="stat-label">草稿</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card mini">
          <div class="stat-info">
            <div class="stat-value-sm">{{ stats.content_pending }}</div>
            <div class="stat-label">待发布</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card mini success">
          <div class="stat-info">
            <div class="stat-value-sm">{{ stats.content_published }}</div>
            <div class="stat-label">已发布</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card mini">
          <div class="stat-info">
            <div class="stat-value-sm">{{ stats.platforms_connected }}</div>
            <div class="stat-label">已连平台</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-row">
      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>📊</span>
              <span>平台发布分布</span>
            </div>
          </template>
          <div v-if="platformEntries.length === 0" class="empty-chart">
            <span>📊</span>
            <p>暂无发布数据</p>
            <p class="hint">发布内容后这里会显示统计</p>
          </div>
          <div v-else class="platform-list">
            <div v-for="(item, index) in platformEntries" :key="item.platform" class="platform-item">
              <div class="platform-name">
                <span>{{ getPlatformIcon(item.platform) }}</span>
                <span>{{ getPlatformName(item.platform) }}</span>
              </div>
              <div class="platform-bar">
                <div class="bar-fill" :style="{ width: item.percent + '%', background: barColor(index) }"></div>
              </div>
              <div class="platform-count">{{ item.count }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>📈</span>
              <span>内容状态分布</span>
            </div>
          </template>
          <div v-if="stats.content_total === 0" class="empty-chart">
            <span>📈</span>
            <p>暂无内容</p>
            <p class="hint">创建内容后这里会显示状态分布</p>
          </div>
          <div v-else class="platform-list">
            <div v-for="item in contentStatusEntries" :key="item.status" class="platform-item">
              <div class="platform-name">
                <el-tag :type="(item.tagType) as any" size="small">{{ item.label }}</el-tag>
              </div>
              <div class="platform-bar">
                <div class="bar-fill" :style="{ width: item.percent + '%' }"></div>
              </div>
              <div class="platform-count">{{ item.count }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-row">
      <el-col :span="24">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>📋</span>
              <span>汇总数据</span>
            </div>
          </template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="发布记录总数">{{ stats.publish_records_total }}</el-descriptions-item>
            <el-descriptions-item label="调度任务总数">{{ stats.scheduled_tasks_total }}</el-descriptions-item>
            <el-descriptions-item label="已连接平台数">{{ stats.platforms_connected }}</el-descriptions-item>
            <el-descriptions-item label="选题完成率">{{ topicDoneRate }}%</el-descriptions-item>
            <el-descriptions-item label="内容发布率">{{ contentPublishedRate }}%</el-descriptions-item>
            <el-descriptions-item label="审核通过率">{{ reviewApprovedRate }}%</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { statsApi, type Stats as StatsType } from '@/api/cms'
import { getPlatformName, getPlatformIcon, CONTENT_STATUSES, getStatusMeta } from '@/constants'

const stats = ref<StatsType>({
  topics_total: 0,
  materials_total: 0,
  review_pending: 0,
  content_total: 0,
  content_draft: 0,
  content_pending: 0,
  content_published: 0,
  platforms_connected: 0,
  publish_records_total: 0,
  scheduled_tasks_total: 0,
  platform_distribution: {},
})

const loading = ref(false)

const platformEntries = computed(() => {
  const entries = Object.entries(stats.value.platform_distribution || {})
    .map(([platform, count]) => ({ platform, count, percent: 0 }))
    .sort((a, b) => b.count - a.count)
  const max = Math.max(1, ...entries.map(e => e.count))
  entries.forEach(e => e.percent = Math.round((e.count / max) * 100))
  return entries
})

const contentStatusEntries = computed(() => {
  const items = [
    { status: 'draft', count: stats.value.content_draft },
    { status: 'pending', count: stats.value.content_pending },
    { status: 'published', count: stats.value.content_published },
  ]
  const max = Math.max(1, ...items.map(i => i.count))
  return items
    .filter(i => i.count > 0)
    .map(i => {
      const meta = getStatusMeta(CONTENT_STATUSES, i.status)
      return { ...i, label: meta.label, tagType: meta.tagType, percent: Math.round((i.count / max) * 100) }
    })
})

const barColor = (idx: number) => {
  const colors = [
    'linear-gradient(90deg, #00d4ff 0%, #00a8cc 100%)',
    'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
    'linear-gradient(90deg, #f093fb 0%, #f5576c 100%)',
    'linear-gradient(90deg, #4facfe 0%, #00f2fe 100%)',
    'linear-gradient(90deg, #43e97b 0%, #38f9d7 100%)',
    'linear-gradient(90deg, #fa709a 0%, #fee140 100%)',
  ]
  return colors[idx % colors.length]
}

const topicDoneRate = computed(() => {
  if (stats.value.topics_total === 0) return 0
  // 这里简化为：active 的占比
  return 0
})

const contentPublishedRate = computed(() => {
  if (stats.value.content_total === 0) return 0
  return Math.round((stats.value.content_published / stats.value.content_total) * 100)
})

const reviewApprovedRate = computed(() => {
  const reviewed = stats.value.publish_records_total - stats.value.review_pending
  if (stats.value.publish_records_total === 0) return 0
  return Math.round((reviewed / stats.value.publish_records_total) * 100)
})

const loadStats = async () => {
  loading.value = true
  try {
    const data = await statsApi.get()
    stats.value = data
  } catch (e) {
    console.error('Failed to load stats:', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>

<style scoped>
.stats-page { padding: 0; }
.stats-row, .stats-row-2, .charts-row { margin-bottom: 20px; }
.stat-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  transition: all 0.3s ease;
  height: 100%;
}
.stat-card:hover { transform: translateY(-4px); border-color: rgba(0, 212, 255, 0.3); }
.stat-card.highlight {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(26, 26, 46, 0.6) 100%);
  border-color: rgba(0, 212, 255, 0.3);
}
.stat-card.mini { padding: 16px 20px; }
.stat-card.mini.success { border-color: rgba(0, 212, 100, 0.3); }
.stat-icon { font-size: 36px; }
.stat-value { font-size: 32px; font-weight: 700; color: #fff; line-height: 1; }
.stat-value-sm { font-size: 22px; font-weight: 700; color: #fff; line-height: 1; }
.stat-label { font-size: 13px; color: #a0a0b0; margin-top: 6px; }
.chart-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  height: 100%;
}
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; color: #fff; }
.empty-chart { text-align: center; padding: 40px 20px; color: #666; }
.empty-chart span { font-size: 48px; display: block; margin-bottom: 12px; opacity: 0.5; }
.empty-chart .hint { font-size: 12px; color: #444; margin-top: 4px; }
.platform-list { display: flex; flex-direction: column; gap: 16px; }
.platform-item { display: flex; align-items: center; gap: 16px; }
.platform-name { width: 110px; font-size: 13px; color: #e0e0e0; display: flex; align-items: center; gap: 6px; }
.platform-bar {
  flex: 1;
  height: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 5px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00d4ff 0%, #00a8cc 100%);
  border-radius: 5px;
  transition: width 0.5s ease;
}
.platform-count { width: 50px; text-align: right; font-size: 14px; color: #00d4ff; font-weight: 600; }
:deep(.el-descriptions__label) { color: #a0a0b0; }
:deep(.el-descriptions__content) { color: #fff; }
</style>
