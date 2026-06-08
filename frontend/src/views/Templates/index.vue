<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/templates">资源</router-link>
        <span>·</span>
        <span>内容模板</span>
      </div>
      <h1 class="page-title">内容模板</h1>
      <p class="page-subtitle">把常用的内容格式沉淀成模板，新内容一键应用，省去每次重排版的功夫。</p>

      <div class="header-actions">
        <el-button type="primary" @click="openCreate">新建模板</el-button>
      </div>
    </header>

    <el-tabs v-model="activeCategory" @tab-change="loadList" class="ds-tabs">
      <el-tab-pane v-for="c in CATEGORIES" :key="c.value" :label="c.label" :name="c.value" />
    </el-tabs>

    <div v-if="loading && templates.length === 0" class="ds-loading">
      <div class="spinner"></div>
      <div>正在加载模板…</div>
    </div>

    <div v-else-if="templates.length === 0" class="ds-empty">
      <div class="glyph">
        <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="6" y="6" width="20" height="20" rx="2" />
          <path d="M6 12h20M12 12v14" />
        </svg>
      </div>
      <h4>还没有模板</h4>
      <p>沉淀你最常用的内容格式，让创作越来越快。</p>
      <el-button type="primary" @click="openCreate">新建第一个模板</el-button>
    </div>

    <div v-else class="ds-card-grid">
      <article v-for="item in templates" :key="item.id" class="ds-item-card template-card">
        <div class="head">
          <h3 class="title">{{ item.name }}</h3>
          <span class="ds-pill" :class="`ds-pill--${categoryColor(item.category)}`">{{ categoryLabel(item.category) }}</span>
        </div>
        <p v-if="item.description" class="body">{{ item.description }}</p>
        <pre class="preview">{{ truncate(item.body, 240) }}</pre>
        <div class="actions">
          <el-button size="small" type="primary" @click="onUse(item)">使用</el-button>
          <el-button size="small" @click="openEdit(item)">编辑</el-button>
          <el-button size="small" type="danger" text @click="onDelete(item)">删除</el-button>
        </div>
      </article>
    </div>

    <el-dialog v-model="showDialog" :title="isEdit ? '编辑模板' : '新建模板'" width="640px">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="模板名称" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="模板描述..." />
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input v-model="form.body" type="textarea" :rows="10" placeholder="支持 Markdown 语法..." />
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { templateApi, type Template } from '@/api/templates'

const router = useRouter()
const templates = ref<Template[]>([])
const loading = ref(false)
const saving = ref(false)
const activeCategory = ref('all')
const showDialog = ref(false)
const isEdit = ref(false)
const form = ref({ id: '', name: '', category: 'article', description: '', body: '' })

const CATEGORIES = [
  { label: '全部', value: 'all' },
  { label: '文章', value: 'article' },
  { label: '视频脚本', value: 'video_script' },
  { label: '播客', value: 'podcast' },
  { label: '文案', value: 'copy' },
  { label: '其他', value: 'other' },
]

const categoryLabel = (c: string) => CATEGORIES.find(x => x.value === c)?.label || c
const categoryColor = (c: string) => {
  const map: Record<string, string> = { article: 'neutral', video_script: 'warning', podcast: 'success', copy: 'terracotta', other: 'neutral' }
  return map[c] || 'neutral'
}
const truncate = (text: string, len: number) => text.length > len ? text.slice(0, len) + '…' : text

const loadList = async () => {
  loading.value = true
  try { templates.value = await templateApi.list(activeCategory.value === 'all' ? undefined : activeCategory.value) }
  catch (e: any) { ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message)) }
  finally { loading.value = false }
}

const openCreate = () => {
  isEdit.value = false
  form.value = { id: '', name: '', category: 'article', description: '', body: '' }
  showDialog.value = true
}

const openEdit = (t: Template) => {
  isEdit.value = true
  form.value = { id: t.id, name: t.name, category: t.category, description: t.description, body: t.body }
  showDialog.value = true
}

const onSave = async () => {
  if (!form.value.name.trim() || !form.value.body.trim()) {
    ElMessage.warning('请填写名称和正文'); return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await templateApi.update(form.value.id, form.value)
      ElMessage.success('保存成功')
    } else {
      await templateApi.create(form.value)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadList()
  } catch (e: any) { ElMessage.error('保存失败: ' + (e.normalizedMessage || e.message)) }
  finally { saving.value = false }
}

const onUse = (t: Template) => {
  router.push({ path: '/content/create', query: { template: t.id } })
}

const onDelete = async (t: Template) => {
  try {
    await ElMessageBox.confirm(`确定要删除「${t.name}」吗？`, '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  try {
    await templateApi.delete(t.id)
    ElMessage.success('删除成功')
    loadList()
  } catch (e: any) { ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message)) }
}

onMounted(loadList)
</script>

<style scoped>
.ds-tabs { margin-bottom: 24px; }
.template-card .preview {
  background: var(--claude-parchment);
  border: 1px solid var(--claude-border-cream);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  font-family: var(--font-mono);
  font-size: 12px; line-height: 1.6;
  color: var(--claude-olive);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 160px; overflow: hidden;
  margin: 0;
}
</style>
