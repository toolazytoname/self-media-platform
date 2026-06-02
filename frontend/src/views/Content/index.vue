<template>
  <div class="content-page">
    <el-card class="content-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span class="title-icon">📝</span>
            <span>内容列表</span>
            <el-tag v-if="total > 0" size="small" type="info" class="count-tag">{{ total }} 条</el-tag>
          </div>
          <div class="header-actions">
            <el-button @click="onExport('json')">📥 导出 JSON</el-button>
            <el-button @click="onExport('markdown')">📝 导出 MD</el-button>
            <el-button @click="onExport('csv')">📊 导出 CSV</el-button>
            <el-button type="primary" @click="$router.push('/content/create')">
              + 新建内容
            </el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar">
        <el-input v-model="searchKeyword" placeholder="搜索标题/正文..." class="search-input" clearable
                  @keyup.enter="reload" @clear="reload" />
        <el-select v-model="filterStatus" placeholder="状态" clearable @change="reload" style="width: 130px">
          <el-option v-for="s in CONTENT_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filterPlatform" placeholder="平台" clearable @change="reload" style="width: 140px">
          <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
        </el-select>
        <el-button @click="reload">🔄 刷新</el-button>
        <div class="bulk-actions" v-if="selectedIds.length > 0">
          <span class="bulk-label">已选 {{ selectedIds.length }} 项</span>
          <el-button size="small" @click="onBulkUpdateStatus('published')">批量发布</el-button>
          <el-button size="small" @click="onBulkUpdateStatus('archived')">批量归档</el-button>
          <el-button size="small" type="danger" @click="onBulkDelete">批量删除</el-button>
          <el-button size="small" text @click="selectedIds = []">取消选择</el-button>
        </div>
      </div>

      <div v-if="loading && contentList.length === 0" class="loading-state">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <div v-else-if="contentList.length === 0" class="empty-state">
        <span>📝</span>
        <p>暂无内容</p>
        <p class="hint">点击上方按钮创建第一个内容</p>
      </div>

      <div v-else class="content-grid">
        <div v-for="item in contentList" :key="item.id" class="content-card-item" :class="{ selected: selectedIds.includes(item.id) }">
          <div class="card-check">
            <el-checkbox v-model="selectedIds" :value="item.id" />
          </div>
          <div class="card-top">
            <div class="card-title-row">
              <span class="card-title-text" @click="goView(item.id)">{{ item.title }}</span>
              <el-tag :type="(getStatusMeta(CONTENT_STATUSES, item.status).tagType) as any" size="small" class="status-badge">
                {{ getStatusMeta(CONTENT_STATUSES, item.status).label }}
              </el-tag>
            </div>
            <div class="card-meta">
              <span class="platform-badge">{{ getPlatformIcon(item.platform) }} {{ getPlatformName(item.platform) }}</span>
              <span class="date">{{ formatDate(item.updated_at) }}</span>
            </div>
          </div>

          <div v-if="item.body" class="card-body-preview">
            {{ truncate(item.body, 100) }}
          </div>

          <div v-if="item.tags && item.tags.length" class="card-tags">
            <el-tag v-for="tag in item.tags" :key="tag" size="small" class="tag">#{{ tag }}</el-tag>
          </div>

          <div class="card-actions">
            <el-button size="small" @click="goView(item.id)">👁 查看</el-button>
            <el-button size="small" type="primary" @click="goEdit(item.id)">✏️ 编辑</el-button>
            <el-button size="small" @click="onDuplicate(item.id)" title="复制为新草稿">📋 复制</el-button>
            <el-button v-if="canSubmitReview(item.status)" size="small" type="warning" @click="onSubmitReview(item.id)">📋 审核</el-button>
            <el-button size="small" type="danger" @click="onDelete(item.id, item.title)">🗑 删除</el-button>
          </div>
        </div>
      </div>

      <div class="pagination-wrapper" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, total"
          background
          @current-change="loadPage"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { contentApi, type Content } from '@/api/content'
import { CONTENT_STATUSES, PLATFORM_OPTIONS, getStatusMeta, getPlatformName, getPlatformIcon, formatDate } from '@/constants'

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
.content-page {
  padding: 0;
}

.content-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.title-icon {
  font-size: 20px;
}

.count-tag {
  margin-left: 4px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  align-items: center;
}

.search-input {
  width: 240px;
}

.bulk-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  padding: 4px 12px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 8px;
  border: 1px solid rgba(0, 212, 255, 0.3);
}

.bulk-label {
  color: #00d4ff;
  font-size: 13px;
  font-weight: 500;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.content-card-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.3s ease;
  position: relative;
}

.content-card-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(0, 212, 255, 0.2);
  transform: translateY(-2px);
}

.content-card-item.selected {
  border-color: #00d4ff;
  background: rgba(0, 212, 255, 0.05);
}

.card-check {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1;
}

.card-top {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.card-title-text {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  line-height: 1.4;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  cursor: pointer;
  transition: color 0.2s;
}

.card-title-text:hover {
  color: #00d4ff;
}

.status-badge {
  flex-shrink: 0;
  border: none;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #888;
}

.platform-badge {
  background: rgba(102, 126, 234, 0.15);
  color: #a78bfa;
  padding: 2px 8px;
  border-radius: 4px;
}

.date {
  color: #666;
}

.card-body-preview {
  font-size: 13px;
  color: #aaa;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  background: rgba(0, 212, 255, 0.1);
  border: none;
  color: #00d4ff;
  font-size: 11px;
}

.card-actions {
  display: flex;
  gap: 4px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  margin-top: auto;
  flex-wrap: wrap;
}

.card-actions .el-button {
  flex: 1;
  min-width: 60px;
  font-size: 11px;
  padding: 4px 6px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.empty-state,
.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-state span,
.loading-state span {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.empty-state .hint {
  font-size: 13px;
  color: #444;
  margin-top: 8px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.loading-state span {
  font-size: 16px;
}
</style>
