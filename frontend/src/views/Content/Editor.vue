<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/content">内容</router-link>
        <span>·</span>
        <span>{{ isEdit ? '编辑' : '创建' }}</span>
      </div>
      <h1 class="page-title">{{ isEdit ? '编辑内容' : '创建内容' }}</h1>
      <p class="page-subtitle">{{ isEdit ? '修改当前内容，保存后立即生效。' : '新建一篇内容，填写标题、正文、标签和目标平台。' }}</p>
    </header>

    <section class="ds-card editor-form">
      <el-form :model="form" label-position="top" v-loading="loading">
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

        <div class="two-col">
          <el-form-item label="标签">
            <el-select v-model="form.tags" multiple filterable allow-create default-first-option
                       placeholder="选择或输入新标签，回车确认" style="width: 100%">
              <el-option v-for="t in TAG_PRESETS" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="目标平台">
            <el-select v-model="form.platform" placeholder="选择平台" style="width: 100%">
              <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
            </el-select>
          </el-form-item>
        </div>

        <div class="form-actions">
          <el-button @click="goBack">取消</el-button>
          <el-button v-if="isEdit && canSubmitReview" @click="onSubmitReview" :loading="reviewing">
            提交审核
          </el-button>
          <el-button type="primary" @click="onSave" :loading="saving">
            {{ isEdit ? '保存修改' : '创建内容' }}
          </el-button>
        </div>
      </el-form>
    </section>
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
const form = ref({ title: '', body: '', tags: [] as string[], platform: 'all' })
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

const canSubmitReview = computed(() => {
  return currentStatus.value === 'draft' || currentStatus.value === 'failed'
})

const renderedBody = computed(() => {
  return marked.parse(form.value.body || '*(空)*', { async: false }) as string
})

const goBack = () => {
  if (form.value.title || form.value.body) {
    ElMessageBox.confirm('当前有未保存的修改，确定离开?', '提示', {
      confirmButtonText: '离开', cancelButtonText: '继续编辑', type: 'warning',
    }).then(() => router.push('/content')).catch(() => {})
  } else {
    router.push('/content')
  }
}

const loadContent = async (id: string) => {
  loading.value = true
  try {
    const item = await contentApi.get(id)
    form.value = {
      title: item.title, body: item.body,
      tags: [...(item.tags || [])], platform: item.platform,
    }
    currentStatus.value = item.status
  } catch (e: any) {
    ElMessage.error('加载内容失败: ' + e.normalizedMessage)
    router.push('/content')
  } finally { loading.value = false }
}

const loadTemplates = async () => {
  try { templates.value = await templateApi.list() } catch (e) { /* ignore */ }
}

const applyTemplate = () => {
  const t = templates.value.find(x => x.id === selectedTemplate.value)
  if (!t) return
  ElMessageBox.confirm(`应用模板会覆盖当前正文（标题保留）。确定吗？`, '应用模板', {
    confirmButtonText: '应用', cancelButtonText: '取消', type: 'warning',
  }).then(() => {
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
  if (err) { ElMessage.warning(err); return }
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
  } finally { saving.value = false }
}

const onSubmitReview = async () => {
  if (!isEdit.value) return
  try {
    await ElMessageBox.confirm('提交审核后，内容将进入待审核队列', '确认', {
      confirmButtonText: '提交', cancelButtonText: '取消', type: 'info',
    })
  } catch { return }
  reviewing.value = true
  try {
    await contentApi.update(route.params.id as string, form.value)
    await contentApi.submitReview(route.params.id as string)
    ElMessage.success('已提交审核')
    router.push('/content')
  } catch (e: any) {
    ElMessage.error('提交失败: ' + (e.normalizedMessage || e.message))
  } finally { reviewing.value = false }
}

onMounted(() => {
  loadTemplates()
  if (isEdit.value) loadContent(route.params.id as string)
})
</script>

<style scoped>
@media (max-width: 720px) { .two-col { grid-template-columns: 1fr; } }
</style>
