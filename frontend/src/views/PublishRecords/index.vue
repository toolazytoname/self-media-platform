<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/publish-records">工作流</router-link>
        <span>·</span>
        <span>发布记录</span>
      </div>
      <h1 class="page-title">发布记录</h1>
      <p class="page-subtitle">查看内容到各平台的发布历史。失败的任务会显示原因，可以重试。</p>

      <div class="header-actions">
        <el-button @click="onRunDue" :loading="running">执行到期任务</el-button>
        <el-button @click="loadList">刷新</el-button>
      </div>
    </header>

    <div class="ds-filter-bar">
      <el-select v-model="filterStatus" placeholder="状态" clearable @change="loadList" style="width: 160px">
        <el-option v-for="s in PUBLISH_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filterPlatform" placeholder="平台" clearable @change="loadList" style="width: 180px">
        <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
      </el-select>
      <div style="flex: 1"></div>
      <span class="caption">共 {{ total }} 条</span>
    </div>

    <div v-if="loading && list.length === 0" class="ds-loading">
      <div class="spinner"></div>
      <div>正在加载发布记录…</div>
    </div>

    <div v-else-if="filteredList.length === 0" class="ds-empty">
      <div class="glyph">
        <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M8 22V10h16v12M4 22h24M12 14h8M12 18h6" stroke-linecap="round" />
        </svg>
      </div>
      <h4>还没有发布记录</h4>
      <p>从内容详情页发布内容后，任务会出现在这里。</p>
    </div>

    <el-table v-else :data="filteredList" v-loading="loading" stripe class="ds-table">
      <el-table-column label="ID" width="200">
        <template #default="{ row }">
          <code class="mono id-code">{{ row.publish_id.slice(0, 8) }}…</code>
        </template>
      </el-table-column>
      <el-table-column label="内容" prop="content_title" min-width="200" show-overflow-tooltip />
      <el-table-column label="平台" width="140">
        <template #default="{ row }">
          <span class="ds-pill ds-pill--neutral">{{ getPlatformName(row.platform) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <span class="ds-status" :class="statusClass(row.status)">
            <span class="dot"></span>
            {{ getStatusMeta(PUBLISH_STATUSES, row.status).label }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="计划时间" width="180">
        <template #default="{ row }">
          <span class="mono">{{ formatDate(row.scheduled_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="结果" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.error_message" class="ds-pill ds-pill--warning">{{ row.error_message }}</span>
          <span v-else-if="row.url" class="ds-pill ds-pill--success">
            <a :href="row.url" target="_blank" rel="noopener">查看</a>
          </span>
          <span v-else class="caption">—</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { platformApi, type PublishRecord } from '@/api/platforms'
import { schedulerApi } from '@/api/scheduler'
import { PUBLISH_STATUSES, PLATFORM_OPTIONS, getStatusMeta, getPlatformName, formatDate } from '@/constants'

const list = ref<PublishRecord[]>([])
const loading = ref(false)
const running = ref(false)
const filterStatus = ref('')
const filterPlatform = ref('')
const total = computed(() => list.value.length)

const filteredList = computed(() => {
  let res = list.value
  if (filterStatus.value) res = res.filter(r => r.status === filterStatus.value)
  if (filterPlatform.value) res = res.filter(r => r.platform === filterPlatform.value)
  return res
})

const statusClass = (s: string) => {
  if (s === 'success' || s === 'published') return 'ds-status--success'
  if (s === 'pending' || s === 'scheduled') return 'ds-status--warning'
  if (s === 'failed') return 'ds-status--error'
  return 'ds-status--neutral'
}

const loadList = async () => {
  loading.value = true
  try { list.value = await platformApi.listPublishRecords() }
  catch (e: any) { ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message)) }
  finally { loading.value = false }
}

const onRunDue = async () => {
  running.value = true
  try {
    const res = await schedulerApi.runDue()
    ElMessage.success(`已执行 ${res.executed} 个到期任务`)
    loadList()
  } catch (e: any) { ElMessage.error('执行失败: ' + (e.normalizedMessage || e.message)) }
  finally { running.value = false }
}

onMounted(loadList)
</script>

<style scoped>
.ds-table { background: var(--claude-ivory); border-radius: var(--radius-xl); overflow: hidden; }
.ds-table :deep(.ds-pill a) { color: inherit; }
</style>
