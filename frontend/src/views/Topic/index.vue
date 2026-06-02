<template>
  <div class="topic-page">
    <el-card class="topic-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>💡</span>
            <span>选题库</span>
            <el-tag v-if="total > 0" size="small" type="info" class="count-tag">{{ total }} 个</el-tag>
          </div>
          <el-button type="primary" @click="openCreate">+ 新建选题</el-button>
        </div>
      </template>

      <div class="filter-bar">
        <el-select v-model="filterStatus" placeholder="状态" clearable @change="loadList" style="width: 130px">
          <el-option v-for="s in TOPIC_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
      </div>

      <div v-if="loading && topics.length === 0" class="loading-state">加载中...</div>
      <div v-else-if="topics.length === 0" class="empty-state">
        <span>💡</span>
        <p>暂无选题</p>
        <p class="hint">点击上方按钮创建第一个选题</p>
      </div>
      <div v-else class="topic-grid">
        <div v-for="item in topics" :key="item.id" class="topic-card-item">
          <div class="card-header-row">
            <span class="topic-title">{{ item.title }}</span>
            <el-tag :type="getPriorityType(item.priority) as any" size="small">{{ item.priority }}级</el-tag>
          </div>
          <p class="topic-desc">{{ item.description || '暂无描述' }}</p>
          <div class="card-footer">
            <span class="status-tag" :class="item.status">{{ getStatusText(item.status) }}</span>
            <span class="date">{{ formatDate(item.created_at) }}</span>
          </div>
          <div class="card-actions">
            <el-button size="small" @click="openEdit(item)">✏️ 编辑</el-button>
            <el-button size="small" v-if="item.status === 'active'" @click="markDone(item)">✓ 完成</el-button>
            <el-button size="small" type="danger" @click="onDelete(item)">🗑 删除</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑选题' : '新建选题'" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="输入选题标题..." maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="输入选题描述..." />
        </el-form-item>
        <el-form-item label="优先级">
          <el-rate v-model="form.priority" :max="5" show-text :texts="['极低', '较低', '普通', '较高', '极高']" />
        </el-form-item>
        <el-form-item v-if="isEdit" label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="s in TOPIC_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="onSave" :loading="saving">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { topicApi, type Topic } from '@/api/cms'
import { TOPIC_STATUSES, formatDate } from '@/constants'

const topics = ref<Topic[]>([])
const loading = ref(false)
const saving = ref(false)
const filterStatus = ref('')
const showDialog = ref(false)
const isEdit = ref(false)
const total = computed(() => topics.value.length)
const form = ref({
  id: '',
  title: '',
  description: '',
  priority: 3,
  status: 'active',
})

const getPriorityType = (p: number) => {
  if (p >= 5) return 'danger'
  if (p >= 4) return 'warning'
  if (p >= 3) return ''
  if (p >= 2) return 'info'
  return 'info'
}
const getStatusText = (s: string) => TOPIC_STATUSES.find(x => x.value === s)?.label || s

const loadList = async () => {
  loading.value = true
  try {
    topics.value = await topicApi.list(filterStatus.value || undefined)
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message))
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  isEdit.value = false
  form.value = { id: '', title: '', description: '', priority: 3, status: 'active' }
  showDialog.value = true
}

const openEdit = (t: Topic) => {
  isEdit.value = true
  form.value = { ...t }
  showDialog.value = true
}

const onSave = async () => {
  if (!form.value.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await topicApi.update(form.value.id, {
        title: form.value.title,
        description: form.value.description,
        priority: form.value.priority,
        status: form.value.status,
      })
      ElMessage.success('保存成功')
    } else {
      await topicApi.create({
        title: form.value.title,
        description: form.value.description,
        priority: form.value.priority,
      })
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadList()
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.normalizedMessage || e.message))
  } finally {
    saving.value = false
  }
}

const markDone = async (t: Topic) => {
  try {
    await topicApi.update(t.id, { status: 'done' })
    ElMessage.success('已标记为完成')
    loadList()
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e.normalizedMessage || e.message))
  }
}

const onDelete = async (t: Topic) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选题「${t.title}」吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  try {
    await topicApi.delete(t.id)
    ElMessage.success('删除成功')
    loadList()
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message))
  }
}

onMounted(loadList)
</script>

<style scoped>
.topic-page { padding: 0; }
.topic-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; color: #fff; }
.count-tag { margin-left: 4px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 20px; }
.topic-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.topic-card-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.3s ease;
}
.topic-card-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(0, 212, 255, 0.2);
  transform: translateY(-2px);
}
.card-header-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.topic-title { font-size: 15px; font-weight: 600; color: #fff; line-height: 1.4; flex: 1; }
.topic-desc {
  font-size: 13px; color: #888; line-height: 1.5;
  overflow: hidden; text-overflow: ellipsis;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.card-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.status-tag { font-size: 12px; padding: 2px 8px; border-radius: 4px; }
.status-tag.active { background: rgba(0, 212, 255, 0.1); color: #00d4ff; }
.status-tag.done { background: rgba(0, 212, 100, 0.1); color: #00dc64; }
.status-tag.archived { background: rgba(255, 255, 255, 0.1); color: #888; }
.date { font-size: 12px; color: #666; }
.card-actions { display: flex; gap: 6px; }
.card-actions .el-button { flex: 1; font-size: 12px; padding: 6px 8px; }
.empty-state, .loading-state { text-align: center; padding: 60px 20px; color: #666; }
.empty-state span { font-size: 48px; display: block; margin-bottom: 16px; }
.empty-state .hint { font-size: 13px; color: #444; margin-top: 8px; }
</style>
