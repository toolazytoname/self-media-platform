<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/stats">系统</router-link>
        <span>·</span>
        <span>数据</span>
      </div>
      <h1 class="page-title">数据</h1>
      <p class="page-subtitle">一目了然地看你的内容产出、待办、和分发情况。</p>
    </header>

    <!-- Top metric tiles -->
    <section class="metric-row">
      <article class="metric-tile">
        <div class="metric-icon">
          <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="4" y="3" width="12" height="14" rx="1.5" />
            <path d="M7 6h6M7 9h6M7 12h4" stroke-linecap="round" />
          </svg>
        </div>
        <div class="metric-label">内容总数</div>
        <div class="metric-value">{{ stats.content_total }}</div>
        <div class="metric-foot">
          <span class="ds-status ds-status--success"><span class="dot"></span>草稿 {{ stats.content_draft }}</span>
        </div>
      </article>
      <article class="metric-tile">
        <div class="metric-icon">
          <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M10 3v2M10 15v2M3 10h2M15 10h2M5 5l1.4 1.4M13.6 13.6L15 15M5 15l1.4-1.4M13.6 6.4L15 5" stroke-linecap="round" />
            <circle cx="10" cy="10" r="2" />
          </svg>
        </div>
        <div class="metric-label">选题总数</div>
        <div class="metric-value">{{ stats.topics_total }}</div>
        <div class="metric-foot">
          <span class="caption">选题 / 想法</span>
        </div>
      </article>
      <article class="metric-tile">
        <div class="metric-icon">
          <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="3" width="14" height="14" rx="2" />
            <circle cx="7.5" cy="7.5" r="1.5" />
            <path d="M3 13l4-4 3 3 3-3 4 4" stroke-linejoin="round" />
          </svg>
        </div>
        <div class="metric-label">素材总数</div>
        <div class="metric-value">{{ stats.materials_total }}</div>
        <div class="metric-foot">
          <span class="caption">图片 / 视频 / 音频</span>
        </div>
      </article>
      <article class="metric-tile metric-tile--accent">
        <div class="metric-icon">
          <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="10" cy="10" r="7.5" />
            <path d="M10 6v4l2.5 2.5" stroke-linecap="round" />
          </svg>
        </div>
        <div class="metric-label">待审核</div>
        <div class="metric-value">{{ stats.review_pending }}</div>
        <div class="metric-foot">
          <span class="ds-pill ds-pill--warning">需处理</span>
        </div>
      </article>
    </section>

    <div class="charts-grid">
      <!-- Platform distribution -->
      <section class="ds-card chart-card">
        <h2 class="ds-card__title">平台发布分布</h2>
        <p class="ds-card__lede">已发布到各平台的内容数量。</p>
        <div v-if="platformEntries.length === 0" class="ds-empty ds-empty--compact">
          <p>暂无发布数据</p>
          <p class="caption">发布内容后这里会显示统计</p>
        </div>
        <div v-else class="chart-canvas">
          <Doughnut :data="platformChartData" :options="doughnutOptions" />
        </div>
      </section>

      <!-- Content status distribution -->
      <section class="ds-card chart-card">
        <h2 class="ds-card__title">内容状态分布</h2>
        <p class="ds-card__lede">各状态下内容数量的占比。</p>
        <div v-if="stats.content_total === 0" class="ds-empty ds-empty--compact">
          <p>暂无内容</p>
          <p class="caption">创建内容后这里会显示状态分布</p>
        </div>
        <div v-else class="chart-canvas">
          <Bar :data="contentStatusChartData" :options="barOptions" />
        </div>
      </section>
    </div>

    <section class="ds-card" style="margin-top: 32px">
      <h2 class="ds-card__title">汇总</h2>
      <p class="ds-card__lede">平台、账号、模板、发布记录等基础数据的总量。</p>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="发布记录">{{ stats.publish_records_total }}</el-descriptions-item>
        <el-descriptions-item label="已连接平台">{{ stats.platforms_connected }}</el-descriptions-item>
        <el-descriptions-item label="调度任务">{{ stats.scheduled_tasks_total }}</el-descriptions-item>
      </el-descriptions>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Chart, registerables } from 'chart.js'
import { Doughnut, Bar } from 'vue-chartjs'
import { statsApi, type Stats } from '@/api/cms'
import { getPlatformName, CONTENT_STATUSES } from '@/constants'

// Register all chart.js components once at module load.
Chart.register(...registerables)

const stats = ref<any>({
  content_total: 0, content_draft: 0, content_pending: 0, content_published: 0,
  topics_total: 0, materials_total: 0, review_pending: 0,
  publish_records_total: 0, scheduled_tasks_total: 0, platforms_connected: 0,
  platform_distribution: {} as Record<string, number>,
})

// Apple×Claude design system palette (tokens.css)
const COLORS = ['#c96442', '#d97757', '#10b981', '#3898ec', '#87867f', '#5e5d59']

const platformEntries = computed(() => {
  const obj: Record<string, number> = stats.value.platform_distribution || {}
  const total = Object.values(obj).reduce((s, v) => s + (v || 0), 0)
  if (total === 0) return []
  return Object.entries(obj)
    .map(([platform, count]) => ({ platform, count }))
    .sort((a, b) => b.count - a.count)
})

const platformChartData = computed(() => ({
  labels: platformEntries.value.map(e => getPlatformName(e.platform)),
  datasets: [{
    data: platformEntries.value.map(e => e.count),
    backgroundColor: platformEntries.value.map((_, i) => COLORS[i % COLORS.length]),
    borderColor: 'var(--claude-ivory, #faf9f5)',
    borderWidth: 2,
  }],
}))

const contentStatusChartData = computed(() => {
  const draft = stats.value.content_draft || 0
  const pending = stats.value.content_pending || 0
  const published = stats.value.content_published || 0
  return {
    labels: ['草稿', '待审核', '已发布'],
    datasets: [{
      data: [draft, pending, published],
      backgroundColor: ['#87867f', '#d97757', '#10b981'],
      borderRadius: 6,
      borderSkipped: false,
    }],
  }
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' as const, labels: { boxWidth: 12, padding: 12 } },
  },
  cutout: '60%',
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y' as const,
  plugins: { legend: { display: false } },
  scales: {
    x: { beginAtZero: true, ticks: { precision: 0 } },
    y: { grid: { display: false } },
  },
}

const load = async () => {
  try {
    const resp = await statsApi.get()
    stats.value = { ...stats.value, ...resp }
  } catch (e: any) {
    ElMessage.error('加载统计失败: ' + (e.normalizedMessage || e.message))
  }
}

onMounted(load)
</script>

<style scoped>
.metric-row {
  display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  margin-bottom: 32px;
}
.metric-tile {
  background: var(--claude-ivory);
  border: 1px solid var(--claude-border-cream);
  border-radius: var(--radius-xl);
  padding: 24px;
  display: flex; flex-direction: column; gap: 8px;
  position: relative;
}
.metric-tile .metric-icon {
  position: absolute; top: 20px; right: 20px;
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: var(--claude-parchment);
  border: 1px solid var(--claude-border-cream);
  border-radius: 10px;
  color: var(--claude-terracotta);
}
.metric-tile--accent .metric-icon {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.10);
  color: var(--claude-coral);
}
.metric-tile--accent {
  background: var(--claude-ink);
  border-color: var(--claude-ink);
  color: var(--claude-ivory);
}
.metric-tile--accent .metric-label,
.metric-tile--accent .metric-foot { color: var(--claude-warm-silver); }
.metric-label {
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--claude-stone); font-weight: 500;
}
.metric-value {
  font-family: var(--font-serif);
  font-size: 48px; font-weight: 500; line-height: 1;
  color: inherit;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.metric-foot { font-size: 12px; }

.charts-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
}
.chart-canvas {
  position: relative;
  height: 280px;
  padding: 8px 0;
}
.ds-empty--compact { padding: 32px 16px; }
</style>
