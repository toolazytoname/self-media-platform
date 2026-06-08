<template>
  <div v-if="content">
    <header class="page-header view-header">
      <div class="breadcrumb">
        <router-link to="/content">内容</router-link>
        <span>·</span>
        <span>详情</span>
      </div>

      <div class="header-row">
        <div class="title-block">
          <h1 class="page-title">{{ content.title }}</h1>
          <div class="page-subtitle meta-row">
            <span class="ds-pill ds-pill--neutral">{{ getPlatformName(content.platform) }}</span>
            <span class="ds-status" :class="statusClass(content.status)">
              <span class="dot"></span>
              {{ getStatusMeta(CONTENT_STATUSES, content.status).label }}
            </span>
          </div>
        </div>
        <div class="header-actions">
          <el-button @click="$router.push('/content')">返回</el-button>
          <el-button @click="onDuplicate">复制</el-button>
          <el-button type="primary" @click="goEdit">编辑</el-button>
          <el-button type="danger" text @click="onDelete">删除</el-button>
        </div>
      </div>
    </header>

    <section class="ds-card view-card" v-loading="loading">
      <div class="meta-grid">
        <div>
          <div class="caption">创建</div>
          <div class="meta-value">{{ formatDate(content.created_at) }}</div>
        </div>
        <div>
          <div class="caption">更新</div>
          <div class="meta-value">{{ formatDate(content.updated_at) }}</div>
        </div>
        <div>
          <div class="caption">状态</div>
          <div class="meta-value">{{ getStatusMeta(CONTENT_STATUSES, content.status).label }}</div>
        </div>
        <div>
          <div class="caption">平台</div>
          <div class="meta-value">{{ getPlatformName(content.platform) }}</div>
        </div>
      </div>

      <div v-if="content.tags && content.tags.length" class="tags-row">
        <span v-for="t in content.tags" :key="t" class="ds-pill ds-pill--neutral">#{{ t }}</span>
      </div>

      <el-divider />

      <article class="markdown-body" v-html="renderedBody"></article>
    </section>
  </div>
  <div v-else-if="!loading" class="ds-empty">
    <div class="glyph">
      <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="16" cy="16" r="12" />
        <path d="M12 12l8 8M20 12l-8 8" stroke-linecap="round" />
      </svg>
    </div>
    <h4>内容不存在</h4>
    <p>这条内容可能已被删除，或链接已失效。</p>
    <el-button @click="$router.push('/content')">返回列表</el-button>
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

const renderedBody = computed(() => marked.parse(content.value?.body || '*(空)*', { async: false }) as string)

const statusClass = (s: string) => {
  if (s === 'published' || s === 'completed') return 'ds-status--success'
  if (s === 'pending') return 'ds-status--warning'
  if (s === 'failed' || s === 'archived') return 'ds-status--error'
  return 'ds-status--neutral'
}

const load = async (id: string) => {
  loading.value = true
  try { content.value = await contentApi.get(id) }
  catch (e: any) { ElMessage.error('加载失败: ' + e.normalizedMessage) }
  finally { loading.value = false }
}

const goEdit = () => content.value && router.push(`/content/edit/${content.value.id}`)

const onDuplicate = async () => {
  if (!content.value) return
  try {
    const newItem = await contentApi.duplicate(content.value.id)
    ElMessage.success('已复制为草稿')
    router.push(`/content/edit/${newItem.id}`)
  } catch (e: any) { ElMessage.error('复制失败: ' + (e.normalizedMessage || e.message)) }
}

const onDelete = async () => {
  if (!content.value) return
  try {
    await ElMessageBox.confirm(`确定要删除「${content.value.title}」吗？`, '删除确认', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
  } catch { return }
  try {
    await contentApi.delete(content.value.id)
    ElMessage.success('删除成功')
    router.push('/content')
  } catch (e: any) { ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message)) }
}

onMounted(() => load(route.params.id as string))
</script>

<style scoped>
.view-card { max-width: 900px; }
.header-row {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 24px;
  flex-wrap: wrap;
}
.title-block { flex: 1; min-width: 0; }
.meta-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.meta-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
  margin-bottom: 20px;
}
.meta-grid > div { display: flex; flex-direction: column; gap: 4px; }
.meta-value { font-size: 14px; color: var(--claude-ink); font-variant-numeric: tabular-nums; }
.tags-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.markdown-body {
  font-family: var(--font-serif); font-size: 17px; line-height: 1.85;
  color: var(--claude-ink);
}
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) {
  font-family: var(--font-serif); font-weight: 500;
  color: var(--claude-ink); margin: 32px 0 12px;
  letter-spacing: -0.01em;
}
.markdown-body :deep(h1) { font-size: 32px; }
.markdown-body :deep(h2) { font-size: 24px; }
.markdown-body :deep(h3) { font-size: 20px; }
.markdown-body :deep(p) { margin: 0 0 16px; }
.markdown-body :deep(a) { color: var(--claude-terracotta); }
.markdown-body :deep(code) {
  font-family: var(--font-mono); font-size: 0.9em;
  background: var(--claude-border-cream); padding: 2px 6px; border-radius: 4px;
}
.markdown-body :deep(pre) {
  background: var(--claude-ink); color: var(--claude-ivory);
  padding: 16px; border-radius: var(--radius-lg); overflow-x: auto;
  font-family: var(--font-mono); font-size: 13px;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--claude-terracotta);
  padding: 4px 0 4px 16px; margin: 16px 0;
  color: var(--claude-olive);
  font-style: italic;
}
@media (max-width: 640px) {
  .meta-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
