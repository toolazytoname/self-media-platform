<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/sources">资源</router-link>
        <span>·</span>
        <span>来源管理</span>
      </div>
      <h1 class="page-title">来源管理</h1>
      <p class="page-subtitle">
        集中管理 PDF / 公开网页 / 纯文本 / NotebookLM notebook 等素材来源。
        创建 NotebookLM 来源后,可以触发 AI 生成 audio / video / quiz / 等多种格式,一鱼多吃。
      </p>

      <div class="header-actions">
        <el-button @click="checkNotebookLMAuth" :loading="checkingAuth">
          连接 NotebookLM
        </el-button>
        <el-button type="primary" @click="openCreate">添加来源</el-button>
      </div>
    </header>

    <!-- NotebookLM 状态条 -->
    <el-alert
      v-if="nlmStatus"
      :type="nlmStatus.authenticated ? 'success' : 'warning'"
      :closable="false"
      class="nlm-banner"
    >
      <template #title>
        <span v-if="nlmStatus.authenticated">
          NotebookLM 已登录({{ nlmStatus.profile }})
        </span>
        <span v-else>
          NotebookLM 未登录 — 请在终端跑:<code class="cmd">{{ nlmStatus.login_command }}</code>
          <el-button link type="primary" size="small" @click="checkNotebookLMAuth">重试</el-button>
        </span>
      </template>
    </el-alert>

    <el-tabs v-model="activeType" @tab-change="loadList" class="ds-tabs">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="PDF" name="pdf" />
      <el-tab-pane label="URL" name="url" />
      <el-tab-pane label="文本" name="text" />
      <el-tab-pane label="NotebookLM" name="notebooklm" />
    </el-tabs>

    <div v-if="loading && sources.length === 0" class="ds-loading">
      <div class="spinner"></div>
      <div>正在加载来源…</div>
    </div>

    <div v-else-if="sources.length === 0" class="ds-empty">
      <h4>还没有来源</h4>
      <p>支持 PDF / URL / 文本 / NotebookLM 四种类型。NotebookLM 来源可触发 AI 生成 audio / video / quiz 等多格式内容。</p>
      <el-button type="primary" @click="openCreate">添加第一个来源</el-button>
    </div>

    <div v-else class="ds-card-grid sources-grid">
      <article v-for="s in sources" :key="s.id" class="ds-item-card source-card">
        <div class="source-head">
          <span class="ds-pill" :class="typePillClass(s.type)">{{ TYPE_LABELS[s.type] || s.type }}</span>
          <span v-if="s.chapter_count > 0" class="ds-pill ds-pill--neutral">{{ s.chapter_count }} 章</span>
        </div>
        <h3 class="title" :title="s.name">{{ s.name }}</h3>
        <div class="meta mono">
          <template v-if="s.type === 'notebooklm'">
            notebook: {{ s.notebook_id?.slice(0, 16) }}…
          </template>
          <template v-else-if="s.path">{{ s.path }}</template>
          <template v-else-if="s.url">{{ s.url }}</template>
          <template v-else-if="s.content_preview">{{ s.content_preview.slice(0, 80) }}</template>
        </div>
        <div v-if="s.research_query" class="research">
          <span class="ds-pill ds-pill--terracotta">research</span>
          <span class="query">{{ s.research_query }}</span>
        </div>
        <div v-if="s.source_refs && s.source_refs.length" class="refs">
          <span v-for="(r, i) in s.source_refs.slice(0, 3)" :key="i" class="ds-pill ds-pill--neutral" :title="r.content">
            {{ r.type }}: {{ truncate(r.content, 30) }}
          </span>
          <span v-if="s.source_refs.length > 3" class="ds-pill ds-pill--neutral">+{{ s.source_refs.length - 3 }}</span>
        </div>
        <div class="actions">
          <el-button v-if="s.type === 'notebooklm'" size="small" @click="openGenerate(s)">触发生成</el-button>
          <el-button size="small" type="danger" text @click="onDelete(s)">删除</el-button>
        </div>
      </article>
    </div>

    <!-- 创建来源弹窗 -->
    <el-dialog v-model="showCreate" :title="'添加来源'" width="560px" @closed="resetForm">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如:小狗钱钱(精读)" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.type" style="width: 100%" @change="onTypeChange">
            <el-option label="PDF 文件(自动切章节)" value="pdf" />
            <el-option label="URL 公开网页" value="url" />
            <el-option label="纯文本" value="text" />
            <el-option label="NotebookLM notebook" value="notebooklm" />
          </el-select>
        </el-form-item>

        <template v-if="form.type === 'pdf'">
          <el-form-item label="PDF 路径" required>
            <el-input v-model="form.path" placeholder="/abs/path/to/book.pdf" />
          </el-form-item>
        </template>
        <template v-else-if="form.type === 'url'">
          <el-form-item label="URL" required>
            <el-input v-model="form.url" placeholder="https://..." />
          </el-form-item>
        </template>
        <template v-else-if="form.type === 'text'">
          <el-form-item label="内容" required>
            <el-input v-model="form.content" type="textarea" :rows="6" placeholder="粘贴文本..." />
          </el-form-item>
        </template>
        <template v-else-if="form.type === 'notebooklm'">
          <el-alert v-if="nlmStatus && !nlmStatus.authenticated" type="warning" :closable="false" class="nlm-form-alert">
            <template #title>
              请先在终端跑 <code class="cmd">{{ nlmStatus.login_command }}</code> 登录 NotebookLM
            </template>
          </el-alert>
          <el-form-item label="URL 列表(每行一个)">
            <el-input v-model="urlsText" type="textarea" :rows="3" placeholder="https://example.com/a&#10;https://example.com/b" />
          </el-form-item>
          <el-form-item label="本地文件路径(每行一个)">
            <el-input v-model="filesText" type="textarea" :rows="2" placeholder="/abs/path/to/article.pdf" />
          </el-form-item>
          <el-form-item label="Web 搜索(可选,触发 add-research)">
            <el-input v-model="form.query" placeholder="如:AI safety 2026 latest papers" />
          </el-form-item>
          <el-form-item label="CLI Profile">
            <el-input v-model="form.profile" placeholder="default" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="onCreate" :loading="creating">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 触发生成弹窗 -->
    <el-dialog v-model="showGenerate" :title="`触发生成 — ${currentSource?.name || ''}`" width="560px">
      <el-form label-position="top">
        <el-form-item label="Artifact 类型">
          <el-select v-model="genForm.type" style="width: 100%">
            <el-option v-for="t in ARTIFACT_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="生成指令(可选)">
          <el-input v-model="genForm.instructions" type="textarea" :rows="3" placeholder="如:面向产品经理的深度讲解,15 分钟左右" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerate = false">取消</el-button>
        <el-button @click="onBatchGenerate" :loading="batchGenerating">
          一鱼多吃(选中全部短任务)
        </el-button>
        <el-button type="primary" @click="onGenerate" :loading="generating">
          生成
        </el-button>
      </template>
    </el-dialog>

    <!-- Artifacts 列表弹窗 -->
    <el-dialog v-model="showArtifacts" :title="`产出 — ${currentSource?.name || ''}`" width="720px">
      <div v-if="artifacts.length === 0" class="ds-empty">
        <p>暂无产出。先点击"触发生成"。</p>
      </div>
      <div v-else class="artifact-list">
        <article v-for="a in artifacts" :key="a.id" class="artifact-row">
          <div class="artifact-head">
            <span class="ds-pill ds-pill--terracotta">{{ a.type }}</span>
            <span class="ds-pill" :class="statusPillClass(a.status)">{{ a.status }}</span>
            <span class="mono created-at">{{ a.created_at }}</span>
          </div>
          <div v-if="a.local_path" class="path mono">
            <a :href="a.local_path" target="_blank">{{ a.local_path }}</a>
          </div>
          <div v-if="a.error" class="error">{{ a.error }}</div>
        </article>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  sourcesApi,
  type Source,
  type SourceType,
  type NotebookLMAuthStatus,
  type CreateSourceInput,
  type GenerateArtifactInput,
} from '@/api/sources'

const TYPE_LABELS: Record<SourceType, string> = {
  pdf: 'PDF',
  url: 'URL',
  text: '文本',
  notebooklm: 'NotebookLM',
}

const ARTIFACT_OPTIONS = [
  { value: 'audio', label: 'Audio Overview(播客)' },
  { value: 'video', label: 'Video Overview' },
  { value: 'cinematic-video', label: 'Cinematic Video' },
  { value: 'slide-deck', label: 'Slide Deck' },
  { value: 'infographic', label: 'Infographic' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'flashcards', label: 'Flashcards' },
  { value: 'report', label: 'Report' },
  { value: 'mind-map', label: 'Mind Map' },
  { value: 'data-table', label: 'Data Table' },
]

const sources = ref<Source[]>([])
const loading = ref(false)
const activeType = ref<string>('all')

const showCreate = ref(false)
const creating = ref(false)
const form = reactive<CreateSourceInput>({
  name: '',
  type: 'pdf',
  path: '',
  url: '',
  content: '',
  urls: [],
  files: [],
  query: '',
  profile: 'default',
  metadata: {},
})
const urlsText = ref('')
const filesText = ref('')

const showGenerate = ref(false)
const generating = ref(false)
const batchGenerating = ref(false)
const currentSource = ref<Source | null>(null)
const genForm = reactive<GenerateArtifactInput>({ type: 'audio', instructions: '' })

const showArtifacts = ref(false)
const artifacts = ref<Array<Record<string, unknown>>>([])

const nlmStatus = ref<NotebookLMAuthStatus | null>(null)
const checkingAuth = ref(false)

const truncate = (s: string, n: number) => (s.length > n ? s.slice(0, n) + '…' : s)

const typePillClass = (t: SourceType) => {
  return {
    pdf: 'ds-pill--terracotta',
    url: 'ds-pill--neutral',
    text: 'ds-pill--neutral',
    notebooklm: 'ds-pill--terracotta',
  }[t] || 'ds-pill--neutral'
}

const statusPillClass = (s: string) => {
  if (s === 'completed') return 'ds-pill--success'
  if (s === 'failed') return 'ds-pill--danger'
  return 'ds-pill--neutral'
}

const onTypeChange = () => {
  form.path = ''
  form.url = ''
  form.content = ''
  form.urls = []
  form.files = []
  form.query = ''
  form.profile = 'default'
  urlsText.value = ''
  filesText.value = ''
}

const resetForm = () => {
  form.name = ''
  form.type = 'pdf'
  form.path = ''
  form.url = ''
  form.content = ''
  form.urls = []
  form.files = []
  form.query = ''
  form.profile = 'default'
  form.metadata = {}
  urlsText.value = ''
  filesText.value = ''
}

const openCreate = () => {
  resetForm()
  showCreate.value = true
}

const checkNotebookLMAuth = async () => {
  checkingAuth.value = true
  try {
    nlmStatus.value = await sourcesApi.authCheck(form.profile || 'default')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '探测失败'
    ElMessage.error(`NotebookLM 探测失败: ${msg}`)
  } finally {
    checkingAuth.value = false
  }
}

const loadList = async () => {
  loading.value = true
  try {
    const t = activeType.value === 'all' ? undefined : (activeType.value as SourceType)
    sources.value = await sourcesApi.list(t)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '加载失败'
    ElMessage.error(`加载来源失败: ${msg}`)
  } finally {
    loading.value = false
  }
}

const onCreate = async () => {
  if (!form.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  if (form.type === 'notebooklm') {
    const urls = urlsText.value.split('\n').map((s) => s.trim()).filter(Boolean)
    const files = filesText.value.split('\n').map((s) => s.trim()).filter(Boolean)
    if (!urls.length && !files.length && !form.query?.trim()) {
      ElMessage.warning('NotebookLM 来源至少要填 URL / 文件 / 搜索关键词 之一')
      return
    }
    form.urls = urls
    form.files = files
  } else if (form.type === 'pdf' && !form.path) {
    ElMessage.warning('请填写 PDF 路径')
    return
  } else if (form.type === 'url' && !form.url) {
    ElMessage.warning('请填写 URL')
    return
  } else if (form.type === 'text' && !form.content) {
    ElMessage.warning('请填写文本内容')
    return
  }
  creating.value = true
  try {
    const created = await sourcesApi.create(form)
    ElMessage.success('已创建')
    showCreate.value = false
    await loadList()
    if (created.type === 'notebooklm') {
      checkNotebookLMAuth()
    }
  } catch (e: unknown) {
    // 后端 401 返 {code, message, login_command} 形式
    const err = e as { normalizedMessage?: string; response?: { data?: { detail?: unknown } } }
    const detail = err.response?.data?.detail
    if (
      detail &&
      typeof detail === 'object' &&
      'code' in detail &&
      (detail as { code?: string }).code === 'notebooklm_not_authenticated'
    ) {
      const d = detail as { message: string; login_command: string }
      ElMessageBox.alert(
        `${d.message}\n\n请在终端执行:\n${d.login_command}\n\n完成后点击"重试"按钮。`,
        'NotebookLM 未登录',
        { confirmButtonText: '我知道了' }
      )
    } else {
      ElMessage.error(err.normalizedMessage || '创建失败')
    }
  } finally {
    creating.value = false
  }
}

const onDelete = async (s: Source) => {
  try {
    await ElMessageBox.confirm(`确定删除「${s.name}」?此操作不可恢复。`, '确认删除', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await sourcesApi.delete(s.id)
    ElMessage.success('已删除')
    loadList()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '删除失败'
    ElMessage.error(`删除失败: ${msg}`)
  }
}

const openGenerate = async (s: Source) => {
  currentSource.value = s
  genForm.type = 'audio'
  genForm.instructions = ''
  showGenerate.value = true
  // 同时拉 artifacts 列表
  try {
    const list = await sourcesApi.listArtifacts(s.id)
    artifacts.value = list.artifacts
  } catch {
    artifacts.value = []
  }
}

const onGenerate = async () => {
  if (!currentSource.value) return
  generating.value = true
  try {
    const artifact = await sourcesApi.generate(currentSource.value.id, genForm)
    if (artifact.status === 'completed' && artifact.local_path) {
      ElMessage.success(`已生成: ${artifact.local_path}`)
    } else if (artifact.status === 'polling') {
      ElMessage.info(`已触发生成任务(${artifact.type}),后续可下载`)
    } else {
      ElMessage.warning(`状态: ${artifact.status}${artifact.error ? ' — ' + artifact.error : ''}`)
    }
    // 刷新 artifacts
    const list = await sourcesApi.listArtifacts(currentSource.value.id)
    artifacts.value = list.artifacts
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '生成失败'
    ElMessage.error(`生成失败: ${msg}`)
  } finally {
    generating.value = false
  }
}

const onBatchGenerate = async () => {
  if (!currentSource.value) return
  batchGenerating.value = true
  try {
    // 一鱼多吃:触发短任务集
    const types = ['quiz', 'flashcards', 'report', 'mind-map']
    const result = await sourcesApi.batchGenerate(
      currentSource.value.id,
      types,
      genForm.instructions
    )
    ElMessage.success(`批量完成: ${result.succeeded}/${result.batch_size}`)
    const list = await sourcesApi.listArtifacts(currentSource.value.id)
    artifacts.value = list.artifacts
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '批量生成失败'
    ElMessage.error(msg)
  } finally {
    batchGenerating.value = false
  }
}

onMounted(() => {
  loadList()
  checkNotebookLMAuth()
})
</script>

<style scoped>
.nlm-banner {
  margin-bottom: 16px;
}
.nlm-form-alert {
  margin-bottom: 16px;
}
.nlm-banner .cmd,
.nlm-form-alert .cmd {
  background: var(--ds-surface-2, #f5f5f5);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 0.9em;
  margin: 0 4px;
}
.source-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 180px;
}
.source-head {
  display: flex;
  gap: 8px;
  align-items: center;
}
.source-card .title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  line-height: 1.4;
}
.source-card .meta {
  font-size: 12px;
  color: var(--ds-text-2, #666);
  word-break: break-all;
}
.source-card .research {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.source-card .research .query {
  color: var(--ds-text-2, #666);
}
.source-card .refs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.source-card .actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
  padding-top: 8px;
}
.artifact-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 480px;
  overflow-y: auto;
}
.artifact-row {
  border: 1px solid var(--ds-border, #e5e5e5);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.artifact-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.artifact-row .created-at {
  font-size: 11px;
  color: var(--ds-text-2, #888);
  margin-left: auto;
}
.artifact-row .path a {
  color: var(--ds-link, #5b8def);
  text-decoration: none;
  font-size: 12px;
}
.artifact-row .error {
  color: var(--ds-danger, #d33);
  font-size: 12px;
}
</style>
