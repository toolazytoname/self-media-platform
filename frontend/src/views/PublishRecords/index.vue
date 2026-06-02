<template>
  <div class="publish-page">
    <el-card class="publish-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>📤</span>
            <span>发布记录</span>
            <el-tag v-if="total > 0" size="small" type="info" class="count-tag">{{ total }} 条</el-tag>
          </div>
          <div class="header-actions">
            <el-button @click="onRunDue" :loading="running" type="warning">
              ▶ 执行到期任务
            </el-button>
            <el-button @click="loadList" :icon="undefined">🔄 刷新</el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar">
        <el-select v-model="filterStatus" placeholder="状态" clearable @change="loadList" style="width: 140px">
          <el-option v-for="s in PUBLISH_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filterPlatform" placeholder="平台" clearable @change="loadList" style="width: 140px">
          <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
        </el-select>
      </div>

      <el-table :data="filteredList" v-loading="loading" stripe style="width: 100%">
        <el-table-column label="ID" prop="publish_id" width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="id-code">{{ row.publish_id.slice(0, 8) }}…</code>
          </template>
        </el-table-column>
        <el-table-column label="内容" prop="content_title" min-width="180" show-overflow-tooltip />
        <el-table-column label="平台" width="120">
          <template #default="{ row }">
            <span class="platform-cell">
              {{ getPlatformIcon(row.platform) }} {{ getPlatformName(row.platform) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="(getStatusMeta(PUBLISH_STATUSES, row.status).tagType) as any" size="small">
              {{ getStatusMeta(PUBLISH_STATUSES, row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="计划时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.scheduled_time) }}
          </template>
        </el-table-column>
        <el-table-column label="执行时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.executed_at) }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="goContent(row.content_id)" v-if="row.content_id">
              查看内容
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-state">
            <span>📤</span>
            <p>暂无发布记录</p>
            <p class="hint">从内容详情页发布内容后会出现在这里</p>
          </div>
        </template>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { platformApi, type PublishRecord } from '@/api/platforms'
import { schedulerApi } from '@/api/scheduler'
import { PUBLISH_STATUSES, PLATFORM_OPTIONS, getStatusMeta, getPlatformName, getPlatformIcon, formatDate } from '@/constants'

const router = useRouter()

const list = ref<PublishRecord[]>([])
const loading = ref(false)
const running = ref(false)
const filterStatus = ref('')
const filterPlatform = ref('')
const total = computed(() => list.value.length)

const filteredList = computed(() => {
  let res = list.value
  if (filterStatus.value) {
    res = res.filter(r => r.status === filterStatus.value)
  }
  if (filterPlatform.value) {
    res = res.filter(r => r.platform === filterPlatform.value)
  }
  return res
})

const loadList = async () => {
  loading.value = true
  try {
    list.value = await platformApi.listPublishRecords()
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message))
  } finally {
    loading.value = false
  }
}

const onRunDue = async () => {
  running.value = true
  try {
    const res = await schedulerApi.runDue()
    ElMessage.success(`已执行 ${res.executed} 个到期任务`)
    loadList()
  } catch (e: any) {
    ElMessage.error('执行失败: ' + (e.normalizedMessage || e.message))
  } finally {
    running.value = false
  }
}

const goContent = (id: string) => router.push(`/content/view/${id}`)

onMounted(loadList)
</script>

<style scoped>
.publish-page {
  padding: 0;
}

.publish-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.count-tag {
  margin-left: 4px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.id-code {
  font-family: monospace;
  font-size: 12px;
  color: #888;
}

.platform-cell {
  font-size: 13px;
  color: #e0e0e0;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #666;
}

.empty-state span {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.empty-state .hint {
  font-size: 12px;
  color: #444;
  margin-top: 4px;
}
</style>
