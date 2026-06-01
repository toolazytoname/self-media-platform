<template>
  <div class="review-page">
    <el-card class="review-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>✅</span>
            <span>审核队列</span>
            <el-badge :value="pendingCount" type="primary" class="badge" />
          </div>
        </div>
      </template>

      <div v-if="reviewTasks.length === 0" class="empty-state">
        <span>✅</span>
        <p>暂无待审核内容</p>
        <p class="hint">内容创建后将出现在这里</p>
      </div>

      <div v-else class="review-grid">
        <div v-for="item in reviewTasks" :key="item.id" class="review-card-item">
          <div class="card-top">
            <span class="content-title">{{ item.content_title }}</span>
            <el-tag :type="getStatusType(item.status)" size="small">
              {{ getStatusText(item.status) }}
            </el-tag>
          </div>
          
          <div v-if="item.reviewer_comment" class="review-comment">
            📝 {{ item.reviewer_comment }}
          </div>

          <div class="card-footer">
            <span class="date">{{ formatDate(item.created_at) }}</span>
            <div class="action-buttons" v-if="item.status === 'pending'">
              <el-button size="small" type="success" @click="approve(item.id)">
                ✓ 通过
              </el-button>
              <el-button size="small" type="danger" @click="reject(item.id)">
                ✗ 拒绝
              </el-button>
            </div>
            <span v-else class="reviewed-label">已处理</span>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const reviewTasks = ref<any[]>([])

const pendingCount = computed(() => {
  return reviewTasks.value.filter(t => t.status === 'pending').length
})

const fetchTasks = async () => {
  try {
    const res = await axios.get('/api/cms/review/tasks')
    reviewTasks.value = res.data
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  }
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝'
  }
  return map[status] || status
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

const approve = async (id: string) => {
  try {
    await axios.put(`/api/cms/review/${id}?status=approved`)
    ElMessage.success('已通过')
    fetchTasks()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const reject = async (id: string) => {
  try {
    await axios.put(`/api/cms/review/${id}?status=rejected`)
    ElMessage.success('已拒绝')
    fetchTasks()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

onMounted(fetchTasks)
</script>

<style scoped>
.review-page {
  padding: 0;
}

.review-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.card-header {
  display: flex;
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

.badge {
  margin-left: 8px;
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

.review-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.review-card-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.3s ease;
}

.review-card-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(0, 212, 255, 0.2);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.content-title {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  line-height: 1.4;
  flex: 1;
}

.review-comment {
  font-size: 13px;
  color: #888;
  background: rgba(255, 255, 255, 0.03);
  padding: 10px 12px;
  border-radius: 8px;
  line-height: 1.5;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.date {
  font-size: 12px;
  color: #666;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.reviewed-label {
  font-size: 12px;
  color: #888;
}
</style>