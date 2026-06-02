<template>
  <div class="review-page">
    <el-card class="review-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>✅</span>
            <span>审核队列</span>
            <el-badge :value="pendingCount" type="warning" class="badge" />
            <el-tag v-if="tasks.length > 0" size="small" type="info" class="count-tag">{{ tasks.length }} 总</el-tag>
          </div>
          <el-radio-group v-model="filterStatus" @change="loadList" size="small">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="pending">待审核</el-radio-button>
            <el-radio-button value="approved">已通过</el-radio-button>
            <el-radio-button value="rejected">已拒绝</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <div v-if="loading && tasks.length === 0" class="loading-state">加载中...</div>
      <div v-else-if="tasks.length === 0" class="empty-state">
        <span>✅</span>
        <p>{{ filterStatus === 'pending' ? '没有待审核内容' : '暂无审核任务' }}</p>
        <p class="hint">从内容列表点击"提交审核"后会出现在这里</p>
      </div>
      <div v-else class="review-grid">
        <div v-for="item in tasks" :key="item.id" class="review-card-item">
          <div class="card-top">
            <span class="content-title" @click="goContent(item.content_id)">{{ item.content_title }}</span>
            <el-tag :type="(getStatusMeta(REVIEW_STATUSES, item.status).tagType) as any" size="small">
              {{ getStatusMeta(REVIEW_STATUSES, item.status).label }}
            </el-tag>
          </div>

          <div v-if="item.content_body" class="content-body-preview">
            {{ truncate(item.content_body, 120) }}
          </div>

          <div v-if="item.reviewer_comment" class="review-comment">
            📝 {{ item.reviewer_comment }}
          </div>

          <div class="card-footer">
            <span class="date">{{ formatDate(item.created_at) }}</span>
            <div class="action-buttons" v-if="item.status === 'pending'">
              <el-button size="small" type="success" @click="approve(item)">✓ 通过</el-button>
              <el-button size="small" type="danger" @click="reject(item)">✗ 拒绝</el-button>
            </div>
            <span v-else class="reviewed-label">
              {{ formatDate(item.reviewed_at) }}
            </span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 拒绝原因对话框 -->
    <el-dialog v-model="showRejectDialog" title="拒绝原因" width="420px">
      <el-input v-model="rejectComment" type="textarea" :rows="3" placeholder="请说明拒绝原因..." />
      <template #footer>
        <el-button @click="showRejectDialog = false">取消</el-button>
        <el-button type="danger" @click="confirmReject" :loading="rejecting">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reviewApi, type ReviewTask } from '@/api/cms'
import { REVIEW_STATUSES, getStatusMeta, formatDate } from '@/constants'

const router = useRouter()
const tasks = ref<ReviewTask[]>([])
const loading = ref(false)
const rejecting = ref(false)
const showRejectDialog = ref(false)
const rejectComment = ref('')
const rejectTarget = ref<ReviewTask | null>(null)
const filterStatus = ref('')

const pendingCount = computed(() => tasks.value.filter(t => t.status === 'pending').length)

const truncate = (text: string, len: number) => text.length > len ? text.slice(0, len) + '…' : text

const goContent = (id: string) => router.push(`/content/view/${id}`)

const loadList = async () => {
  loading.value = true
  try {
    tasks.value = await reviewApi.list(filterStatus.value || undefined)
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message))
  } finally {
    loading.value = false
  }
}

const approve = async (item: ReviewTask) => {
  try {
    await ElMessageBox.confirm('通过后内容状态将变为"已发布"', '确认', {
      confirmButtonText: '通过', cancelButtonText: '取消', type: 'success',
    })
  } catch { return }
  try {
    await reviewApi.update(item.id, { status: 'approved' })
    ElMessage.success('已通过')
    loadList()
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e.normalizedMessage || e.message))
  }
}

const reject = (item: ReviewTask) => {
  rejectTarget.value = item
  rejectComment.value = ''
  showRejectDialog.value = true
}

const confirmReject = async () => {
  if (!rejectTarget.value) return
  rejecting.value = true
  try {
    await reviewApi.update(rejectTarget.value.id, {
      status: 'rejected',
      comment: rejectComment.value || '未通过',
    })
    ElMessage.success('已拒绝')
    showRejectDialog.value = false
    loadList()
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e.normalizedMessage || e.message))
  } finally {
    rejecting.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.review-page { padding: 0; }
.review-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}
.card-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; color: #fff; }
.badge { margin-left: 8px; }
.count-tag { margin-left: 4px; }
.review-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
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
.review-card-item:hover { background: rgba(255, 255, 255, 0.05); border-color: rgba(0, 212, 255, 0.2); }
.card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.content-title { font-size: 15px; font-weight: 600; color: #fff; line-height: 1.4; flex: 1; cursor: pointer; transition: color 0.2s; }
.content-title:hover { color: #00d4ff; }
.content-body-preview {
  font-size: 13px; color: #888; line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
  padding: 8px 10px;
  border-radius: 6px;
}
.review-comment { font-size: 13px; color: #888; background: rgba(255, 71, 87, 0.05); border-left: 3px solid #ff4757; padding: 10px 12px; border-radius: 4px; line-height: 1.5; }
.card-footer { display: flex; justify-content: space-between; align-items: center; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.05); }
.date { font-size: 12px; color: #666; }
.action-buttons { display: flex; gap: 8px; }
.reviewed-label { font-size: 12px; color: #888; }
.empty-state, .loading-state { text-align: center; padding: 60px 20px; color: #666; }
.empty-state span { font-size: 48px; display: block; margin-bottom: 16px; }
.empty-state .hint { font-size: 13px; color: #444; margin-top: 8px; }
</style>
