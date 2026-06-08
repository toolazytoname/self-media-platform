<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/review">工作流</router-link>
        <span>·</span>
        <span>审核</span>
      </div>
      <h1 class="page-title">审核队列</h1>
      <p class="page-subtitle">在这里处理待审核内容。通过后会进入发布流程，拒绝会退回作者修改。</p>

      <div class="header-actions">
        <el-radio-group v-model="filterStatus" @change="loadList" size="default">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="pending">待审核</el-radio-button>
          <el-radio-button value="approved">已通过</el-radio-button>
          <el-radio-button value="rejected">已拒绝</el-radio-button>
        </el-radio-group>
      </div>
    </header>

    <div v-if="loading && tasks.length === 0" class="ds-loading">
      <div class="spinner"></div>
      <div>正在加载审核任务…</div>
    </div>

    <div v-else-if="tasks.length === 0" class="ds-empty">
      <div class="glyph">
        <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M8 16l5 5 11-12" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <h4>{{ filterStatus === 'pending' ? '没有待审核内容' : '队列为空' }}</h4>
      <p>{{ filterStatus === 'pending' ? '从内容列表提交审核后，任务会出现在这里。' : '试试切换到其他筛选。' }}</p>
    </div>

    <div v-else class="ds-card-grid">
      <article v-for="item in tasks" :key="item.id" class="ds-item-card review-card">
        <div class="head">
          <h3 class="title" @click="goContent(item.content_id)">{{ item.content_title }}</h3>
          <span class="ds-status" :class="statusClass(item.status)">
            <span class="dot"></span>
            {{ getStatusMeta(REVIEW_STATUSES, item.status).label }}
          </span>
        </div>
        <p v-if="item.content_body" class="body">{{ truncate(item.content_body, 140) }}</p>
        <div v-if="item.reviewer_comment" class="review-comment">
          <span class="ds-pill ds-pill--warning">审核意见</span>
          <span>{{ item.reviewer_comment }}</span>
        </div>
        <div class="meta">
          <span class="caption">提交时间</span>
          <span class="mono">{{ formatDate(item.created_at) }}</span>
        </div>
        <div class="actions" v-if="item.status === 'pending'">
          <el-button size="small" type="success" @click="approve(item)">通过</el-button>
          <el-button size="small" type="danger" @click="reject(item)">拒绝</el-button>
        </div>
      </article>
    </div>

    <el-dialog v-model="showRejectDialog" title="拒绝审核" width="480px">
      <el-form label-position="top">
        <el-form-item label="拒绝原因">
          <el-input v-model="rejectComment" type="textarea" :rows="3" placeholder="请说明拒绝原因..." />
        </el-form-item>
      </el-form>
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
const statusClass = (s: string) => {
  if (s === 'approved') return 'ds-status--success'
  if (s === 'pending') return 'ds-status--warning'
  if (s === 'rejected') return 'ds-status--error'
  return 'ds-status--neutral'
}

const loadList = async () => {
  loading.value = true
  try { tasks.value = await reviewApi.list(filterStatus.value || undefined) }
  catch (e: any) { ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message)) }
  finally { loading.value = false }
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
  } catch (e: any) { ElMessage.error('操作失败: ' + (e.normalizedMessage || e.message)) }
}

const reject = (item: ReviewTask) => {
  rejectTarget.value = item
  rejectComment.value = ''
  showRejectDialog.value = true
}

const confirmReject = async () => {
  if (!rejectTarget.value) return
  if (!rejectComment.value.trim()) {
    ElMessage.warning('请填写拒绝原因')
    return
  }
  rejecting.value = true
  try {
    await reviewApi.update(rejectTarget.value.id, { status: 'rejected', reviewer_comment: rejectComment.value })
    ElMessage.success('已拒绝')
    showRejectDialog.value = false
    loadList()
  } catch (e: any) { ElMessage.error('操作失败: ' + (e.normalizedMessage || e.message)) }
  finally { rejecting.value = false }
}

onMounted(loadList)
</script>

<style scoped>
.review-card .review-comment {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 12px 16px;
  background: var(--claude-border-cream);
  border-radius: var(--radius-lg);
  font-size: 13px; line-height: 1.55;
  color: var(--claude-olive);
}
.review-card .meta {
  display: flex; align-items: center; gap: 12px;
  font-size: 12px; color: var(--claude-stone);
}
</style>
