<template>
  <div class="topic-page">
    <el-card class="topic-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>💡</span>
            <span>选题库</span>
          </div>
          <el-button type="primary" @click="showDialog = true">
            + 新建选题
          </el-button>
        </div>
      </template>

      <div v-if="topics.length === 0" class="empty-state">
        <span>💡</span>
        <p>暂无选题</p>
        <p class="hint">点击上方按钮创建第一个选题</p>
      </div>

      <div v-else class="topic-grid">
        <div v-for="item in topics" :key="item.id" class="topic-card-item">
          <div class="card-header-row">
            <span class="topic-title">{{ item.title }}</span>
            <el-tag :type="getPriorityType(item.priority)" size="small">{{ item.priority }}级</el-tag>
          </div>
          <p class="topic-desc">{{ item.description || '暂无描述' }}</p>
          <div class="card-footer">
            <span class="status-tag" :class="item.status">{{ getStatusText(item.status) }}</span>
            <span class="date">{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="showDialog" title="新建选题" width="500px" class="dialog">
      <el-form :model="form" label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="输入选题标题..." />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="输入选题描述..." />
        </el-form-item>
        <el-form-item label="优先级">
          <el-rate v-model="form.priority" :max="5" show-text />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="createTopic">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const topics = ref<any[]>([])
const showDialog = ref(false)
const form = ref({
  title: '',
  description: '',
  priority: 3
})

const fetchTopics = async () => {
  try {
    const res = await axios.get('/api/cms/topics')
    topics.value = res.data
  } catch (error) {
    console.error('Failed to fetch topics:', error)
  }
}

const getPriorityType = (priority: number) => {
  if (priority >= 4) return 'danger'
  if (priority >= 3) return 'warning'
  return 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    active: '进行中',
    done: '已完成',
    archived: '已归档'
  }
  return map[status] || status
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

const createTopic = async () => {
  if (!form.value.title) {
    ElMessage.warning('请输入标题')
    return
  }
  try {
    await axios.post('/api/cms/topics', {
      title: form.value.title,
      description: form.value.description,
      priority: form.value.priority
    })
    ElMessage.success('创建成功')
    showDialog.value = false
    fetchTopics()
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

onMounted(fetchTopics)
</script>

<style scoped>
.topic-page {
  padding: 0;
}

.topic-card {
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

.topic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

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

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.topic-title {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  line-height: 1.4;
  flex: 1;
}

.topic-desc {
  font-size: 13px;
  color: #888;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.status-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-tag.active {
  background: rgba(0, 212, 255, 0.1);
  color: #00d4ff;
}

.status-tag.done {
  background: rgba(0, 212, 100, 0.1);
  color: #00dc64;
}

.status-tag.archived {
  background: rgba(255, 255, 255, 0.1);
  color: #888;
}

.date {
  font-size: 12px;
  color: #666;
}

.dialog :deep(.el-dialog) {
  background: #1a1a2e;
  border-radius: 16px;
}
</style>