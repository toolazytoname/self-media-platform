<template>
  <div class="editor-page">
    <el-card class="editor-card">
      <template #header>
        <div class="card-header">
          <el-button text @click="goBack" class="back-btn">
            ← 返回
          </el-button>
          <span class="title">{{ isEdit ? '编辑内容' : '创建内容' }}</span>
          <div v-if="isEdit && currentStatus" class="status-area">
            <el-tag :type="(statusMeta(currentStatus).tagType) as any" size="small">
              {{ statusMeta(currentStatus).label }}
            </el-tag>
          </div>
        </div>
      </template>

      <el-form :model="form" label-position="top" class="content-form" v-loading="loading">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="输入有吸引力的标题" size="large" maxlength="200" show-word-limit />
        </el-form-item>

        <el-form-item label="内容" required>
          <el-tabs v-model="editorMode" class="editor-tabs">
            <el-tab-pane label="编辑" name="edit">
              <el-input
                v-model="form.body"
                type="textarea"
                :rows="16"
                placeholder="支持 Markdown 语法..."
                class="content-textarea"
                maxlength="100000"
                show-word-limit
              />
            </el-tab-pane>
            <el-tab-pane label="预览" name="preview">
              <div class="preview-box markdown-body" v-html="renderedBody"></div>
            </el-tab-pane>
            <el-tab-pane label="从模板" name="template">
              <div class="template-picker">
                <p class="hint">选择一个模板，会用模板正文替换当前编辑器内容（请先备份）</p>
                <el-select v-model="selectedTemplate" placeholder="选择模板" filterable style="width: 100%">
                  <el-option
                    v-for="t in templates"
                    :key="t.id"
                    :label="`${t.name} (${categoryLabel(t.category)})`"
                    :value="t.id"
                  />
                </el-select>
                <el-button type="primary" :disabled="!selectedTemplate" @click="applyTemplate" style="margin-top: 12px">
                  应用模板
                </el-button>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="标签">
              <el-select v-model="form.tags" multiple filterable allow-create
                         default-first-option
                         placeholder="选择或输入新标签，回车确认" style="width: 100%">
                <el-option v-for="t in TAG_PRESETS" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标平台">
              <el-select v-model="form.platform" placeholder="选择平台" style="width: 100%">
                <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <div class="form-actions">
          <el-button @click="goBack">取消</el-button>
          <el-button v-if="isEdit && canSubmitReview" @click="onSubmitReview" :loading="reviewing">
            📋 提交审核
          </el-button>
          <el-button type="primary" @click="onSave" :loading="saving">
            {{ isEdit ? '保存修改' : '创建内容' }}
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { contentApi, type Content } from '@/api/content'
import { templateApi, type Template } from '@/api/templates'
import { TAG_PRESETS, PLATFORM_OPTIONS, CONTENT_STATUSES, getStatusMeta } from '@/constants'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const form = ref({
  title: '',
  body: '',
  tags: [] as string[],
  platform: 'all',
})
const loading = ref(false)
const saving = ref(false)
const reviewing = ref(false)
const editorMode = ref<'edit' | 'preview' | 'template'>('edit')
const currentStatus = ref<string>('')

const templates = ref<Template[]>([])
const selectedTemplate = ref('')

const CATEGORIES = [
  { label: '全部', value: 'all' },
  { label: '文章', value: 'article' },
  { label: '视频脚本', value: 'video_script' },
  { label: '播客', value: 'podcast' },
  { label: '文案', value: 'copy' },
  { label: '其他', value: 'other' },
]
const categoryLabel = (c: string) => CATEGORIES.find(x => x.value === c)?.label || c

const statusMeta = (s: string) => getStatusMeta(CONTENT_STATUSES, s)

const canSubmitReview = computed(() => {
  return currentStatus.value === 'draft' || currentStatus.value === 'failed'
})

const renderedBody = computed(() => {
  return marked.parse(form.value.body || '*(空)*', { async: false }) as string
})

const goBack = () => {
  if (form.value.title || form.value.body) {
    ElMessageBox.confirm('当前有未保存的修改，确定离开?', '提示', {
      confirmButtonText: '离开',
      cancelButtonText: '继续编辑',
      type: 'warning',
    }).then(() => router.push('/content'))
      .catch(() => {/* keep editing */})
  } else {
    router.push('/content')
  }
}

const loadContent = async (id: string) => {
  loading.value = true
  try {
    const item = await contentApi.get(id)
    form.value = {
      title: item.title,
      body: item.body,
      tags: [...(item.tags || [])],
      platform: item.platform,
    }
    currentStatus.value = item.status
  } catch (e: any) {
    ElMessage.error('加载内容失败: ' + e.normalizedMessage)
    router.push('/content')
  } finally {
    loading.value = false
  }
}

const loadTemplates = async () => {
  try {
    templates.value = await templateApi.list()
  } catch (e) {
    // ignore
  }
}

const applyTemplate = () => {
  const t = templates.value.find(x => x.id === selectedTemplate.value)
  if (!t) return
  ElMessageBox.confirm(
    `应用模板会覆盖当前正文（标题保留）。确定吗？`,
    '应用模板',
    { confirmButtonText: '应用', cancelButtonText: '取消', type: 'warning' },
  ).then(() => {
    form.value.body = t.body
    editorMode.value = 'edit'
    ElMessage.success('已应用模板')
  }).catch(() => {})
}

const validate = (): string | null => {
  if (!form.value.title.trim()) return '请填写标题'
  if (!form.value.body.trim()) return '请填写内容'
  if (form.value.title.length > 200) return '标题不能超过 200 字'
  return null
}

const onSave = async () => {
  const err = validate()
  if (err) {
    ElMessage.warning(err)
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await contentApi.update(route.params.id as string, form.value)
      ElMessage.success('保存成功')
    } else {
      await contentApi.create(form.value)
      ElMessage.success('创建成功')
    }
    router.push('/content')
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.normalizedMessage || e.message))
  } finally {
    saving.value = false
  }
}

const onSubmitReview = async () => {
  if (!isEdit.value) return
  try {
    await ElMessageBox.confirm('提交审核后，内容将进入待审核队列', '确认', {
      confirmButtonText: '提交',
      cancelButtonText: '取消',
      type: 'info',
    })
  } catch {
    return
  }
  reviewing.value = true
  try {
    // 先保存当前修改
    await contentApi.update(route.params.id as string, form.value)
    await contentApi.submitReview(route.params.id as string)
    ElMessage.success('已提交审核')
    router.push('/content')
  } catch (e: any) {
    ElMessage.error('提交失败: ' + (e.normalizedMessage || e.message))
  } finally {
    reviewing.value = false
  }
}

onMounted(() => {
  loadTemplates()
  if (isEdit.value) {
    loadContent(route.params.id as string)
  }
})
</script>

<style scoped>
.editor-page {
  max-width: 960px;
  margin: 0 auto;
}

.editor-card {
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

.status-area {
  flex: 0 0 auto;
}

.content-form {
  padding: 20px 0;
}

.content-textarea {
  font-size: 15px;
  line-height: 1.8;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
}

.editor-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}

.preview-box {
  min-height: 200px;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  color: #e0e0e0;
  line-height: 1.8;
  font-size: 15px;
}

/* Markdown 样式 */
:deep(.markdown-body) h1, :deep(.markdown-body) h2, :deep(.markdown-body) h3,
:deep(.markdown-body) h4, :deep(.markdown-body) h5, :deep(.markdown-body) h6 {
  color: #00d4ff;
  margin-top: 16px;
  margin-bottom: 8px;
}

:deep(.markdown-body) h1 { font-size: 24px; }
:deep(.markdown-body) h2 { font-size: 20px; }
:deep(.markdown-body) h3 { font-size: 18px; }

:deep(.markdown-body) p {
  margin: 8px 0;
  white-space: pre-wrap;
}

:deep(.markdown-body) code {
  background: rgba(0, 0, 0, 0.4);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  color: #ff9f43;
}

:deep(.markdown-body) pre {
  background: rgba(0, 0, 0, 0.4);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

:deep(.markdown-body) pre code {
  background: transparent;
  padding: 0;
  color: #e0e0e0;
}

:deep(.markdown-body) ul, :deep(.markdown-body) ol {
  padding-left: 24px;
  margin: 8px 0;
}

:deep(.markdown-body) li {
  margin: 4px 0;
}

:deep(.markdown-body) blockquote {
  border-left: 3px solid #00d4ff;
  padding-left: 12px;
  color: #a0a0b0;
  margin: 8px 0;
}

:deep(.markdown-body) a {
  color: #00d4ff;
  text-decoration: none;
}

:deep(.markdown-body) a:hover {
  text-decoration: underline;
}

:deep(.markdown-body) table {
  border-collapse: collapse;
  margin: 12px 0;
}

:deep(.markdown-body) th, :deep(.markdown-body) td {
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 8px 12px;
}

:deep(.markdown-body) th {
  background: rgba(0, 212, 255, 0.05);
}

.template-picker {
  padding: 20px 0;
}

.template-picker .hint {
  color: #a0a0b0;
  font-size: 13px;
  margin-bottom: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  margin-top: 24px;
}
</style>
