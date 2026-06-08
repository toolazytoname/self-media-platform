<template>
  <div>
    <!-- Page header (Claude editorial) -->
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/content">内容</router-link>
        <span>·</span>
        <span>列表</span>
      </div>
      <h1 class="page-title">内容管理</h1>
      <p class="page-subtitle">管理你的选题、稿件和已发布内容。支持多平台、批量操作、状态流转。</p>

      <div class="header-actions">
        <el-button @click="onExport('json')">导出 JSON</el-button>
        <el-button @click="onExport('markdown')">导出 Markdown</el-button>
        <el-button @click="onExport('csv')">导出 CSV</el-button>
        <el-button type="primary" @click="$router.push('/content/create')">
          新建内容
        </el-button>
      </div>
    </header>

    <!-- Filter bar -->
    <div class="ds-filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索标题或正文..." class="grow" clearable
                @keyup.enter="reload" @clear="reload" />
      <el-select v-model="filterStatus" placeholder="状态" clearable @change="reload" style="width: 140px">
        <el-option v-for="s in CONTENT_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filterPlatform" placeholder="平台" clearable @change="reload" style="width: 160px">
        <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
      </el-select>
      <el-button @click="reload">刷新</el-button>
      <div v-if="selectedIds.length > 0" class="ds-bulk-strip">
        <span class="label">已选 {{ selectedIds.length }} 项</span>
        <el-button size="small" @click="onBulkUpdateStatus('published')">批量发布</el-button>
        <el-button size="small" @click="onBulkUpdateStatus('archived')">批量归档</el-button>
        <el-button size="small" type="danger" @click="onBulkDelete">批量删除</el-button>
        <el-button size="small" text @click="selectedIds = []">取消</el-button>
      </div>
    </div>

    <!-- Loading / Empty / Grid -->
    <div v-if="loading && contentList.length === 0" class="ds-loading">
      <div class="spinner"></div>
      <div>正在加载内容…</div>
    </div>

    <div v-else-if="contentList.length === 0" class="ds-empty">
      <div class="glyph">
        <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="6" y="6" width="20" height="20" rx="3" />
          <path d="M11 12h10M11 16h10M11 20h6" stroke-linecap="round" />
        </svg>
      </div>
      <h4>还没有内容</h4>
      <p>从新建内容开始，或者从 AI 工具一键生成你的第一篇稿件。</p>
      <el-button type="primary" @click="$router.push('/content/create')">新建内容</el-button>
    </div>

    <div v-else class="ds-card-grid">
      <article v-for="item in contentList" :key="item.id" class="ds-item-card" :class="{ 'is-selected': selectedIds.includes(item.id) }">
        <div class="head">
          <h3 class="title" @click="goView(item.id)">{{ item.title }}</h3>
          <el-checkbox v-model="selectedIds" :value="item.id" />
        </div>

        <div class="meta">
          <span class="ds-pill ds-pill--neutral">{{ getPlatformName(item.platform) }}</span>
          <span class="ds-status" :class="statusClass(item.status)">
            <span class="dot"></span>
            {{ getStatusMeta(CONTENT_STATUSES, item.status).label }}
          </span>
          <span style="margin-left: auto">{{ formatDate(item.updated_at) }}</span>
        </div>

        <p v-if="item.body" class="body">{{ truncate(item.body, 120) }}</p>

        <div v-if="item.tags && item.tags.length" class="tags">
          <span v-for="tag in item.tags" :key="tag" class="ds-pill ds-pill--neutral">#{{ tag }}</span>
        </div>

        <div class="actions">
          <el-button size="small" @click="goView(item.id)">查看</el-button>
          <el-button size="small" type="primary" @click="goEdit(item.id)">编辑</el-button>
          <el-button size="small" v-if="canSubmitReview(item.status)" @click="onSubmitReview(item.id)">提交审核</el-button>
          <el-button size="small" @click="onDuplicate(item.id)">复制</el-button>
          <div style="flex: 1"></div>
          <el-button size="small" type="danger" text @click="onDelete(item.id, item.title)">删除</el-button>
        </div>
      </article>
    </div>

    <!-- Pagination -->
    <div v-if="contentList.length > 0" class="ds-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        background
        @current-change="loadPage"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { contentApi, type Content } from '@/api/content'
import { CONTENT_STATUSES, PLATFORM_OPTIONS, getStatusMeta, getPlatformName, formatDate } from '@/constants'

const router = useRouter()

const contentList = ref<Content[]>([])
const searchKeyword = ref('')
const filterStatus = ref('')
const filterPlatform = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const loading = ref(false)
const selectedIds = ref<string[]>([])

const truncate = (text: string, len: number) => {
  if (!text) return ''
  return text.length > len ? text.slice(0, len) + '…' : text
}

const canSubmitReview = (status: string) => status === 'draft' || status === 'failed'

const statusClass = (s: string) => {
  if (s === 'published' || s === 'completed') return 'ds-status--success'
  if (s === 'pending') return 'ds-status--warning'
  if (s === 'failed' || s === 'archived') return 'ds-status--error'
  return 'ds-status--neutral'
}

const loadPage = async (page: number) => {
  loading.value = true
  try {
    const res = await contentApi.list({
      skip: (page - 1) * pageSize.value,
      limit: pageSize.value,
      status: filterStatus.value || undefined,
      platform: filterPlatform.value || undefined,
      keyword: searchKeyword.value.trim() || undefined,
    })
    contentList.value = res.items
    total.value = res.total
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message))
  } finally {
    loading.value = false
  }
}

const reload = () => {
  currentPage.value = 1
  loadPage(1)
}

const goView = (id: string) => router.push(`/content/view/${id}`)
const goEdit = (id: string) => router.push(`/content/edit/${id}`)

const onDuplicate = async (id: string) => {
  try {
    const newItem = await contentApi.duplicate(id)
    ElMessage.success('已复制为草稿：' + newItem.id)
    loadPage(currentPage.value)
  } catch (e: any) {
    ElMessage.error('复制失败: ' + (e.normalizedMessage || e.message))
  }
}

const onDelete = async (id: string, title: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${title}」吗？此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  try {
    await contentApi.delete(id)
    ElMessage.success('删除成功')
    selectedIds.value = selectedIds.value.filter(x => x !== id)
    if (contentList.value.length === 1 && currentPage.value > 1) {
      currentPage.value -= 1
    }
    loadPage(currentPage.value)
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message))
  }
}

const onSubmitReview = async (id: string) => {
  try {
    await ElMessageBox.confirm('将内容状态改为"待审核"并创建审核任务', '确认', {
      confirmButtonText: '提交', cancelButtonText: '取消', type: 'info',
    })
  } catch { return }
  try {
    await contentApi.submitReview(id)
    ElMessage.success('已提交审核')
    loadPage(currentPage.value)
  } catch (e: any) {
    ElMessage.error('提交失败: ' + (e.normalizedMessage || e.message))
  }
}

const onExport = async (format: 'json' | 'markdown' | 'csv') => {
  try {
    const url = `/api/content/export/all?format=${format}`
    const params = new URLSearchParams()
    if (filterStatus.value) params.set('status', filterStatus.value)
    if (filterPlatform.value) params.set('platform', filterPlatform.value)
    const finalUrl = params.toString() ? `${url}&${params}` : url
    const link = document.createElement('a')
    link.href = finalUrl
    link.download = `contents-${Date.now()}.${format === 'markdown' ? 'md' : format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    ElMessage.success(`已导出为 ${format}`)
  } catch (e: any) {
    ElMessage.error('导出失败: ' + (e.normalizedMessage || e.message))
  }
}

const onBulkDelete = async () => {
  if (selectedIds.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定要批量删除 ${selectedIds.value.length} 个内容吗？此操作不可恢复。`,
      '批量删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { return }
  try {
    const res = await contentApi.bulkDelete(selectedIds.value)
    ElMessage.success(`已删除 ${res.deleted_count} 个内容`)
    selectedIds.value = []
    loadPage(currentPage.value)
  } catch (e: any) {
    ElMessage.error('批量删除失败: ' + (e.normalizedMessage || e.message))
  }
}

const onBulkUpdateStatus = async (status: string) => {
  if (selectedIds.value.length === 0) return
  try {
    const res = await contentApi.bulkUpdate({ ids: selectedIds.value, status })
    ElMessage.success(`已更新 ${res.updated_count} 个内容状态为「${status}」`)
    selectedIds.value = []
    loadPage(currentPage.value)
  } catch (e: any) {
    ElMessage.error('批量更新失败: ' + (e.normalizedMessage || e.message))
  }
}

watch([searchKeyword, filterStatus, filterPlatform], () => {
  clearTimeout((window as any).__contentFilterTimer)
  ;(window as any).__contentFilterTimer = setTimeout(() => {
    if (searchKeyword.value !== '' || filterStatus.value || filterPlatform.value) {
      reload()
    }
  }, 300)
})

onMounted(() => loadPage(1))
</script>

<style scoped>
.ds-pagination {
  display: flex; justify-content: center;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--claude-border-cream);
}
</style>
