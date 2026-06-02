<template>
  <div class="view-page">
    <el-card class="view-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <el-button text @click="$router.push('/content')" class="back-btn">← 返回列表</el-button>
          <span class="title">内容详情</span>
          <div v-if="content" class="header-actions">
            <el-tag :type="(getStatusMeta(CONTENT_STATUSES, content.status).tagType) as any">
              {{ getStatusMeta(CONTENT_STATUSES, content.status).label }}
            </el-tag>
            <el-button type="primary" size="small" @click="goEdit">✏️ 编辑</el-button>
            <el-button size="small" @click="onDuplicate">📋 复制</el-button>
            <el-button size="small" type="danger" @click="onDelete">🗑 删除</el-button>
          </div>
        </div>
      </template>

      <div v-if="content" class="content-detail">
        <h1 class="detail-title">{{ content.title }}</h1>

        <div class="detail-meta">
          <span class="meta-item">
            <span class="meta-label">平台：</span>
            <span class="meta-value">{{ getPlatformName(content.platform) }}</span>
          </span>
          <span class="meta-item">
            <span class="meta-label">创建：</span>
            <span class="meta-value">{{ formatDate(content.created_at) }}</span>
          </span>
          <span class="meta-item">
            <span class="meta-label">更新：</span>
            <span class="meta-value">{{ formatDate(content.updated_at) }}</span>
          </span>
        </div>

        <div v-if="content.tags && content.tags.length" class="detail-tags">
          <el-tag v-for="t in content.tags" :key="t" size="small" class="tag">#{{ t }}</el-tag>
        </div>

        <el-divider />

        <div class="markdown-body" v-html="renderedBody"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { contentApi, type Content } from '@/api/content'
import { CONTENT_STATUSES, getStatusMeta, getPlatformName, formatDate } from '@/constants'

const route = useRoute()
const router = useRouter()

const content = ref<Content | null>(null)
const loading = ref(false)

const renderedBody = computed(() => {
  if (!content.value?.body) return '*(空内容)*'
  return marked.parse(content.value.body, { async: false }) as string
})

const load = async (id: string) => {
  loading.value = true
  try {
    content.value = await contentApi.get(id)
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message))
    router.push('/content')
  } finally {
    loading.value = false
  }
}

const goEdit = () => {
  if (content.value) {
    router.push(`/content/edit/${content.value.id}`)
  }
}

const onDuplicate = async () => {
  if (!content.value) return
  try {
    const newItem = await contentApi.duplicate(content.value.id)
    ElMessage.success('已复制为草稿：' + newItem.id)
    router.push(`/content/edit/${newItem.id}`)
  } catch (e: any) {
    ElMessage.error('复制失败: ' + (e.normalizedMessage || e.message))
  }
}

const onDelete = async () => {
  if (!content.value) return
  try {
    await ElMessageBox.confirm(
      `确定要删除「${content.value.title}」吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  try {
    await contentApi.delete(content.value.id)
    ElMessage.success('删除成功')
    router.push('/content')
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message))
  }
}

onMounted(() => load(route.params.id as string))
</script>

<style scoped>
.view-page {
  max-width: 900px;
  margin: 0 auto;
}

.view-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  color: #00d4ff;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  flex: 1;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.content-detail {
  padding: 8px 0;
}

.detail-title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  line-height: 1.3;
  margin-bottom: 16px;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
}

.meta-label {
  color: #666;
}

.meta-value {
  color: #a0a0b0;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.tag {
  background: rgba(0, 212, 255, 0.1);
  border: none;
  color: #00d4ff;
}

/* Markdown 渲染样式 */
.markdown-body {
  color: #e0e0e0;
  line-height: 1.8;
  font-size: 15px;
}

.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3),
.markdown-body :deep(h4), .markdown-body :deep(h5), .markdown-body :deep(h6) {
  color: #00d4ff;
  margin-top: 24px;
  margin-bottom: 12px;
  line-height: 1.3;
}

.markdown-body :deep(h1) { font-size: 28px; }
.markdown-body :deep(h2) { font-size: 24px; }
.markdown-body :deep(h3) { font-size: 20px; }
.markdown-body :deep(h4) { font-size: 18px; }

.markdown-body :deep(p) {
  margin: 12px 0;
  white-space: pre-wrap;
}

.markdown-body :deep(code) {
  background: rgba(0, 0, 0, 0.4);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  color: #ff9f43;
}

.markdown-body :deep(pre) {
  background: rgba(0, 0, 0, 0.4);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: #e0e0e0;
}

.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 28px;
  margin: 12px 0;
}

.markdown-body :deep(li) {
  margin: 6px 0;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid #00d4ff;
  padding: 8px 12px 8px 16px;
  color: #a0a0b0;
  margin: 16px 0;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 0 6px 6px 0;
}

.markdown-body :deep(a) {
  color: #00d4ff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 16px 0;
  width: 100%;
}

.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 10px 14px;
}

.markdown-body :deep(th) {
  background: rgba(0, 212, 255, 0.05);
  color: #00d4ff;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 12px 0;
}

.markdown-body :deep(hr) {
  border: none;
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 24px 0;
}
</style>
