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
          <div class="field-with-ai">
            <el-input v-model="form.title" placeholder="输入有吸引力的标题" size="large" maxlength="200" show-word-limit />
            <el-button class="ai-btn" :disabled="!form.body" @click="openAiDialog('title')" title="AI 生成标题">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 1l1.5 4 4 1.5-4 1.5L8 12l-1.5-4-4-1.5 4-1.5z" stroke-linejoin="round" fill="currentColor" opacity="0.3" /><path d="M13 9l.7 1.8 1.8.7-1.8.7L13 14l-.7-1.8-1.8-.7 1.8-.7z" fill="currentColor" /></svg>
              <span class="sr-only">AI 生成标题</span>
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="内容" required>
          <div class="editor-split">
            <div class="editor-split__pane">
              <el-input
                v-model="form.body"
                type="textarea"
                :rows="16"
                placeholder="支持 Markdown 语法..."
                class="content-textarea"
                maxlength="100000"
              />
            </div>
            <div class="editor-split__pane editor-split__pane--preview">
              <div class="preview-box markdown-body" v-html="renderedBody"></div>
            </div>
          </div>
          <!-- AI 助手按钮组(Phase C.3) + 模板按钮 -->
          <div class="ai-assist-row">
            <el-button class="ai-btn" :disabled="!form.body" @click="openAiDialog('expand')" size="small">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 4l-2 2 2 2M12 4l2 2-2 2M4 12l-2-2 2-2M12 12l2-2-2-2M5 8h6" stroke-linecap="round" stroke-linejoin="round" /></svg>
              扩写
            </el-button>
            <el-button class="ai-btn" :disabled="!form.body" @click="openAiDialog('summary')" size="small">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h10M3 6h10M3 9h7M3 12h4" stroke-linecap="round" /></svg>
              摘要
            </el-button>
            <el-button class="ai-btn" :disabled="!form.body" @click="openAiDialog('copy')" size="small">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 5h12v8H2z M5 8h6" stroke-linecap="round" /></svg>
              改写文案
            </el-button>
            <el-button class="ai-btn" :disabled="!form.body" @click="openAiDialog('title')" size="small" title="AI 生成标题">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 4h12M2 8h8M2 12h6" stroke-linecap="round" /></svg>
              标题
            </el-button>
            <el-button class="ai-btn" :disabled="!form.body" @click="openAiDialog('tags')" size="small" title="AI 提取标签">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h4l6 6-4 4-6-6V3z" stroke-linejoin="round" /></svg>
              标签
            </el-button>
            <el-divider direction="vertical" />
            <el-button class="ai-btn" size="small" @click="openTemplatePicker">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 2h10v12H3z M3 5h10M5 7h6" stroke-linecap="round" /></svg>
              套模板
            </el-button>
          </div>
        </el-form-item>

        <div class="two-col">
          <el-form-item label="标签">
            <div class="field-with-ai">
              <el-select v-model="form.tags" multiple filterable allow-create default-first-option
                         placeholder="选择或输入新标签，回车确认" style="width: 100%">
                <el-option v-for="t in TAG_PRESETS" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
              <el-button class="ai-btn" :disabled="!form.body" @click="openAiDialog('tags')" title="AI 提取标签">
                <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h4l6 6-4 4-6-6V3z" stroke-linejoin="round" /></svg>
              </el-button>
            </div>
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

        <!-- P2-1: 字数状态条 + 自动保存指示 -->
        <div class="editor-status-bar" data-testid="editor-status-bar">
          <span>{{ form.body.length }} 字符</span>
          <span class="sep">|</span>
          <span>{{ bodyParagraphCount }} 段</span>
          <span class="sep">|</span>
          <span>~{{ estimatedReadMinutes }} 分钟阅读</span>
          <span class="save-status" :class="saveStatusClass" data-testid="save-status">
            <span class="dot" />
            <span>{{ saveStatusText }}</span>
          </span>
        </div>
      </el-form>
    </section>

    <!-- P2-1: 套模板 dialog (从原来的 tab 改成按钮触发) -->
    <el-dialog v-model="templatePicker.show" title="选择模板" width="560px">
      <p class="hint">选择一个模板,会用模板正文替换当前编辑器内容(请先备份)。</p>
      <el-select v-model="templatePicker.selectedId" placeholder="选择模板" filterable style="width: 100%">
        <el-option
          v-for="t in templates"
          :key="t.id"
          :label="`${t.name} (${categoryLabel(t.category)})`"
          :value="t.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="templatePicker.show = false">取消</el-button>
        <el-button type="primary" :disabled="!templatePicker.selectedId" @click="applyTemplate">应用模板</el-button>
      </template>
    </el-dialog>

    <!-- ============ AI 助手弹窗(Phase C.3) ============ -->
    <el-dialog
      v-model="aiDialog.show"
      :title="`AI 助手 · ${aiDialogTitle(aiDialog.module)}`"
      width="640"
    >
      <div v-if="aiDialog.module === 'tags'" class="ai-dialog-body">
        <p class="caption">基于当前正文提取 {{ aiDialog.tagsN }} 个标签,选{{ '{' }}locale{{ '}' }} {{ aiDialog.tagsLocale }}</p>
      </div>
      <div v-else-if="aiDialog.module === 'expand'" class="ai-dialog-body">
        <p class="caption">目标长度 {{ aiDialog.expandLength }}, 语气 {{ aiDialog.expandTone }}</p>
      </div>
      <div v-else-if="aiDialog.module === 'copy'" class="ai-dialog-body">
        <p class="caption">目标平台 {{ aiDialog.copyPlatform }}</p>
      </div>
      <div v-else class="ai-dialog-body">
        <p class="caption">基于当前正文生成</p>
      </div>

      <el-input
        v-model="aiDialog.input"
        type="textarea"
        :rows="6"
        :placeholder="aiDialogPlaceholder"
      />

      <div v-if="aiDialog.result" class="ai-result">
        <pre v-if="aiDialog.module !== 'tags' && aiDialog.module !== 'titles'">{{ aiDialog.result }}</pre>
        <div v-else-if="aiDialog.module === 'tags'" class="ai-tag-pills">
          <el-tag v-for="(t, i) in aiDialog.parsedTags" :key="i" effect="light" style="margin: 4px">
            <span class="caption">[{{ t.group }}]</span> {{ t.text }}
          </el-tag>
        </div>
        <div v-else-if="aiDialog.module === 'titles'" class="ai-titles">
          <div v-for="(t, i) in aiDialog.parsedTitles" :key="i" class="ai-title-row">
            <span class="ai-title-text">{{ t.text }}</span>
            <el-button size="small" type="primary" @click="applyAiResult(t.text)">应用</el-button>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="aiDialog.show = false">关闭</el-button>
        <el-button
          v-if="aiDialog.module !== 'titles' && aiDialog.module !== 'tags'"
          type="primary"
          :loading="aiDialog.loading"
          :disabled="!aiDialog.input"
          @click="runAiAssist"
        >生成</el-button>
        <el-button
          v-if="aiDialog.module === 'titles' && aiDialog.result"
          type="primary"
          @click="aiDialog.show = false"
        >关闭(上方点"应用"逐个采纳)</el-button>
        <el-button
          v-if="aiDialog.module === 'tags' && aiDialog.result"
          type="primary"
          @click="applyTagsToForm"
        >全部应用到标签字段</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { contentApi, type Content } from '@/api/content'
import { templateApi, type Template } from '@/api/templates'
import { aiApi } from '@/api/ai'
import { TAG_PRESETS, PLATFORM_OPTIONS, CONTENT_STATUSES, getStatusMeta, getPlatformName } from '@/constants'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const form = ref({ title: '', body: '', tags: [] as string[], platform: 'all' })
const loading = ref(false)
const saving = ref(false)
const reviewing = ref(false)
const currentStatus = ref<string>('')

const templates = ref<Template[]>([])
// P2-1: 套模板 dialog 状态(从原 selectedTemplate 改为 dialog 形式)
const templatePicker = reactive<{ show: boolean; selectedId: string }>({
  show: false,
  selectedId: '',
})
const openTemplatePicker = () => {
  templatePicker.selectedId = ''
  templatePicker.show = true
}

// P2-1: 字数状态条 + 自动保存指示
const bodyParagraphCount = computed(() => {
  const body = form.value.body || ''
  // 按双换行或单换行分段,过滤空段
  return body.split(/\n\s*\n|\n/).filter((p) => p.trim().length > 0).length
})
const estimatedReadMinutes = computed(() => {
  const chars = form.value.body?.length || 0
  // 中文阅读速度 ~ 300 字/分钟
  return chars === 0 ? 0 : Math.ceil(chars / 300)
})
const saveStatus = ref<'idle' | 'saving' | 'saved'>('idle')
const saveStatusText = computed(() => {
  if (saveStatus.value === 'saving') return '正在保存...'
  // 注意:实际未持久化(仅 UI 指示),避免误导用户
  if (saveStatus.value === 'saved') return '本地已暂存'
  return '未修改'
})
const saveStatusClass = computed(() => saveStatus.value)

// debounce 1s 后"自动保存"(仅 UI 指示,不写盘 — 真保存走 onSave)
let autoSaveTimer: number | undefined
watch(
  () => form.value.body,
  () => {
    if (!form.value.body) {
      saveStatus.value = 'idle'
      return
    }
    saveStatus.value = 'saving'
    if (autoSaveTimer) window.clearTimeout(autoSaveTimer)
    autoSaveTimer = window.setTimeout(() => {
      saveStatus.value = 'saved'
    }, 1000)
  },
)
onUnmounted(() => {
  if (autoSaveTimer) window.clearTimeout(autoSaveTimer)
})

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
  const t = templates.value.find(x => x.id === templatePicker.selectedId)
  if (!t) return
  ElMessageBox.confirm(`应用模板会覆盖当前正文（标题保留）。确定吗？`, '应用模板', {
    confirmButtonText: '应用', cancelButtonText: '取消', type: 'warning',
  }).then(() => {
    form.value.body = t.body
    templatePicker.show = false
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

// ============ AI 助手弹窗(Phase C.3) ============

interface AiDialogState {
  show: boolean
  module: 'title' | 'expand' | 'summary' | 'copy' | 'tags' | 'titles'
  input: string
  result: string
  loading: boolean
  // 副参数
  expandLength: 'short' | 'medium' | 'long'
  expandTone: 'casual' | 'formal' | 'academic'
  copyPlatform: string
  tagsN: number
  tagsLocale: 'zh' | 'en' | 'emoji' | 'mixed'
  parsedTags: { text: string; group: string }[]
  parsedTitles: { text: string }[]
}

const aiDialog = reactive<AiDialogState>({
  show: false,
  module: 'expand',
  input: '',
  result: '',
  loading: false,
  expandLength: 'medium',
  expandTone: 'casual',
  copyPlatform: 'douyin',
  tagsN: 10,
  tagsLocale: 'mixed',
  parsedTags: [],
  parsedTitles: [],
})

const aiDialogTitle = (m: string) => ({
  title: '生成标题', expand: '扩写', summary: '摘要', copy: '改写文案',
  tags: '提取标签', titles: '生成多个标题',
}[m] || m)

const aiDialogPlaceholder = computed(() => {
  // 默认把当前正文塞进 input,user 可以微调
  return aiDialog.module === 'title' ? '可留空(用正文生成);也输入关键词' : '默认从正文取,可修改'
})

const openAiDialog = (m: AiDialogState['module']) => {
  aiDialog.module = m
  aiDialog.input = form.value.body || ''
  aiDialog.result = ''
  aiDialog.parsedTags = []
  aiDialog.parsedTitles = []
  // 模块默认参数
  if (m === 'titles') aiDialog.tagsN = 5
  if (m === 'copy') aiDialog.copyPlatform = form.value.platform !== 'all' ? form.value.platform : 'douyin'
  aiDialog.show = true
}

const runAiAssist = async () => {
  aiDialog.loading = true
  try {
    const input = aiDialog.input || form.value.body
    if (aiDialog.module === 'expand') {
      const r = await aiApi.expandText({
        content: input,
        target_length: aiDialog.expandLength,
        tone: aiDialog.expandTone,
      })
      aiDialog.result = r.expanded
    } else if (aiDialog.module === 'summary') {
      const r = await aiApi.summary(input)
      aiDialog.result = r.summary
    } else if (aiDialog.module === 'copy') {
      const r = await aiApi.copy(input, aiDialog.copyPlatform)
      aiDialog.result = r.copy
    } else if (aiDialog.module === 'title') {
      const r = await aiApi.titles({ content: input, n: 5 })
      aiDialog.parsedTitles = r.titles
      aiDialog.result = r.titles.map(t => t.text).join('\n')
    } else if (aiDialog.module === 'tags') {
      const r = await aiApi.tags({ content: input, n: aiDialog.tagsN, locale: aiDialog.tagsLocale })
      aiDialog.parsedTags = r.tags
      aiDialog.result = r.tags.map(t => `${t.group}|${t.text}`).join('\n')
    }
  } catch (e: any) {
    ElMessage.error('AI 生成失败: ' + (e.normalizedMessage || e.message))
  } finally {
    aiDialog.loading = false
  }
}

const applyAiResult = (text: string) => {
  if (aiDialog.module === 'title') {
    form.value.title = text
    ElMessage.success('已填入标题字段')
  } else {
    form.value.body = text
    ElMessage.success('已替换正文')
  }
  aiDialog.show = false
}

const applyTagsToForm = () => {
  const existing = new Set(form.value.tags)
  for (const t of aiDialog.parsedTags) {
    if (!existing.has(t.text)) {
      form.value.tags.push(t.text)
      existing.add(t.text)
    }
  }
  ElMessage.success(`已添加 ${aiDialog.parsedTags.length} 个标签`)
  aiDialog.show = false
}

onMounted(() => {
  loadTemplates()
  if (isEdit.value) loadContent(route.params.id as string)

  // 处理从 AI 视图跳过来带 ?title= / ?body= / ?add_tag= 预填
  const q = route.query
  if (typeof q.title === 'string' && q.title) form.value.title = q.title
  if (typeof q.body === 'string' && q.body) form.value.body = q.body
  if (typeof q.add_tag === 'string' && q.add_tag) {
    if (!form.value.tags.includes(q.add_tag)) form.value.tags.push(q.add_tag)
  }
})
</script>

<style scoped>
@media (max-width: 720px) { .two-col { grid-template-columns: 1fr; } }

/* ============ Phase C.3: AI 助手按钮 ============ */
.field-with-ai {
  display: flex; gap: 8px; align-items: flex-start;
}
.field-with-ai > .el-input,
.field-with-ai > .el-select { flex: 1; }
.ai-btn {
  background: var(--claude-parchment) !important;
  border: 1px solid var(--claude-border-cream) !important;
  color: var(--claude-terracotta) !important;
  flex-shrink: 0;
  height: 40px;
  padding: 0 12px !important;
}
.ai-btn:hover {
  background: var(--claude-terracotta) !important;
  color: var(--claude-ivory) !important;
  border-color: var(--claude-terracotta) !important;
}
.ai-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.ai-assist-row {
  display: flex; gap: 8px; flex-wrap: wrap;
  margin-top: 12px; padding: 8px;
  background: var(--claude-parchment);
  border-radius: 8px;
}

/* AI 弹窗 */
.ai-dialog-body { margin-bottom: 12px; }
.ai-dialog-body .caption { color: var(--claude-stone); font-size: 13px; }
.ai-result {
  margin-top: 12px; padding: 12px;
  background: var(--claude-parchment);
  border-radius: 8px;
  max-height: 280px; overflow: auto;
}
.ai-result pre {
  font: inherit; font-size: 13px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-word; margin: 0;
}
.ai-tag-pills { display: flex; flex-wrap: wrap; gap: 4px; }
.ai-titles { display: flex; flex-direction: column; gap: 6px; }
.ai-title-row {
  display: flex; gap: 8px; align-items: center;
  padding: 6px 8px; background: var(--claude-ivory);
  border-radius: 6px;
}
.ai-title-text { flex: 1; font-size: 14px; }

/* Split preview (P2-1) */
.editor-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: stretch;
}
.editor-split__pane {
  min-width: 0; /* 防止 flex/grid 子元素溢出 */
}
.editor-split__pane--preview {
  border: 1px solid var(--claude-border-cream);
  border-radius: 4px;
  padding: 12px 16px;
  background: var(--bg-page);
  max-height: 600px;
  overflow: auto;
}
@media (max-width: 960px) {
  .editor-split { grid-template-columns: 1fr; }
}

/* 字数状态条 (P2-1) */
.editor-status-bar {
  display: flex; gap: 16px;
  padding: 8px 12px;
  font-size: 12px; font-family: var(--font-mono);
  color: var(--claude-olive);
  background: var(--bg-page);
  border-top: 1px solid var(--claude-border-cream);
  border-radius: 0 0 4px 4px;
  margin-top: 4px;
}
.editor-status-bar .sep { color: var(--claude-stone); }
.editor-status-bar .save-status {
  margin-left: auto;
  display: flex; align-items: center; gap: 4px;
}
.editor-status-bar .save-status .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--claude-olive);
}
.editor-status-bar .save-status.saving .dot { background: var(--claude-terracotta); }
.editor-status-bar .save-status.saved .dot { background: var(--claude-success); }
</style>
