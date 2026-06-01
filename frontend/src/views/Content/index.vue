<template>
  <div class="content-page">
    <el-card class="content-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span class="title-icon">📝</span>
            <span>内容列表</span>
          </div>
          <el-button type="primary" @click="$router.push('/content/create')">
            + 新建内容
          </el-button>
        </div>
      </template>

      <div class="filter-bar">
        <el-input v-model="searchKeyword" placeholder="搜索内容..." class="search-input" />
        <el-select v-model="filterStatus" placeholder="状态筛选" clearable>
          <el-option label="草稿" value="draft" />
          <el-option label="待审核" value="pending" />
          <el-option label="已发布" value="published" />
          <el-option label="失败" value="failed" />
        </el-select>
      </div>

      <div class="content-list">
        <div v-if="contentList.length === 0" class="empty-state">
          <span>📝</span>
          <p>暂无内容</p>
          <p class="hint">点击上方按钮创建第一个内容</p>
        </div>

        <div v-else class="content-grid">
          <div v-for="item in contentList" :key="item.id" class="content-card-item">
            <div class="card-top">
              <div class="card-title-row">
                <span class="card-title-text">{{ item.title }}</span>
                <el-tag :type="getStatusType(item.status)" size="small" class="status-badge">
                  {{ getStatusText(item.status) }}
                </el-tag>
              </div>
              <div class="card-meta">
                <span class="platform-badge">🌐 {{ getPlatformName(item.platform) }}</span>
                <span class="date">{{ formatDate(item.created_at) }}</span>
              </div>
            </div>
            
            <div class="card-tags" v-if="item.tags && item.tags.length">
              <el-tag v-for="tag in item.tags" :key="tag" size="small" class="tag">#{{ tag }}</el-tag>
            </div>

            <div class="card-actions">
              <el-button size="small" @click="viewContent(item.id)">查看</el-button>
              <el-button size="small" type="primary" @click="editContent(item.id)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteContent(item.id)">删除</el-button>
            </div>
          </div>
        </div>
      </div>

      <div class="pagination-wrapper" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const contentList = ref<any[]>([])
const searchKeyword = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const platformMap: Record<string, string> = {
  douyin: '抖音',
  bilibili: 'B站',
  xiaohongshu: '小红书',
  toutiao: '头条',
  wechat: '公众号',
  youtube: 'YouTube',
  all: '全部平台'
}

const getPlatformName = (key: string) => platformMap[key] || key

const fetchContent = async () => {
  try {
    const res = await axios.get('/api/content/')
    contentList.value = res.data
    total.value = res.data.length
  } catch (error) {
    console.error('Failed to fetch content:', error)
  }
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    draft: 'info',
    pending: 'warning',
    published: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    draft: '草稿',
    pending: '待审核',
    published: '已发布',
    failed: '失败'
  }
  return map[status] || status
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

const viewContent = (id: string) => {
  console.log('view', id)
}

const editContent = (id: string) => {
  console.log('edit', id)
}

const deleteContent = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这篇内容吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await axios.delete(`/api/content/${id}`)
    ElMessage.success('删除成功')
    fetchContent()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(fetchContent)
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

.filter-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.search-input {
  width: 280px;
}

/* 卡片式列表 */
.content-list {
  min-height: 200px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-state span {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.empty-state .hint {
  font-size: 13px;
  color: #444;
  margin-top: 8px;
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
}

.content-card-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(0, 212, 255, 0.2);
  transform: translateY(-2px);
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
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  margin-top: auto;
}

.card-actions .el-button {
  flex: 1;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
</style>