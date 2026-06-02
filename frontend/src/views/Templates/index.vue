<template>
  <div class="templates-page">
    <el-card class="templates-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>📋</span>
            <span>内容模板</span>
            <el-tag v-if="templates.length > 0" size="small" type="info" class="count-tag">
              {{ templates.length }} 个
            </el-tag>
          </div>
          <el-button type="primary" @click="openCreate">+ 新建模板</el-button>
        </div>
      </template>

      <el-tabs v-model="activeCategory" @tab-change="loadList" class="filter-tabs">
        <el-tab-pane v-for="c in CATEGORIES" :key="c.value" :label="c.label" :name="c.value" />
      </el-tabs>

      <div v-if="loading && templates.length === 0" class="loading-state">加载中...</div>
      <div v-else-if="templates.length === 0" class="empty-state">
        <span>📋</span>
        <p>暂无模板</p>
        <p class="hint">点击上方按钮创建第一个内容模板</p>
      </div>
      <div v-else class="template-grid">
        <div v-for="item in templates" :key="item.id" class="template-card">
          <div class="card-top">
            <span class="tpl-name">{{ item.name }}</span>
            <el-tag size="small" :type="categoryTagType(item.category) as any">
              {{ categoryLabel(item.category) }}
            </el-tag>
          </div>
          <p v-if="item.description" class="tpl-desc">{{ item.description }}</p>
          <pre class="tpl-preview">{{ truncate(item.body, 200) }}</pre>
          <div class="card-actions">
            <el-button size="small" @click="onUse(item)">✨ 使用</el-button>
            <el-button size="small" @click="openEdit(item)">✏️ 编辑</el-button>
            <el-button size="small" type="danger" @click="onDelete(item)">🗑 删除</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 新建/编辑模板对话框 -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑模板' : '新建模板'" width="640px">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="模板名称" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in CATEGORIES.filter(x => x.value !== 'all')" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="模板用途说明..." />
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input v-model="form.body" type="textarea" :rows="10" placeholder="模板内容（支持 Markdown）" />
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
import { contentApi } from '@/api/content'

const router = useRouter()

const CATEGORIES = [
  { label: '全部', value: 'all' },
  { label: '文章', value: 'article' },
  { label: '视频脚本', value: 'video_script' },
  { label: '播客', value: 'podcast' },
  { label: '文案', value: 'copy' },
  { label: '其他', value: 'other' },
]

const templates = ref<Template[]>([])
const loading = ref(false)
const saving = ref(false)
const activeCategory = ref('all')
const showDialog = ref(false)
const isEdit = ref(false)

const form = ref({
  id: '',
  name: '',
  category: 'article',
  description: '',
  body: '',
})

const categoryLabel = (c: string) => CATEGORIES.find(x => x.value === c)?.label || c
const categoryTagType = (c: string) => {
  return ({ article: '', video_script: 'warning', podcast: 'success', copy: 'info', other: '' } as any)[c] || ''
}

const truncate = (text: string, len: number) => text.length > len ? text.slice(0, len) + '…' : text

const loadList = async () => {
  loading.value = true
  try {
    templates.value = await templateApi.list(activeCategory.value === 'all' ? undefined : activeCategory.value)
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message))
  } finally {
    loading.value = false
  }
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
    ElMessage.warning('请填写名称和正文')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await templateApi.update(form.value.id, {
        name: form.value.name,
        category: form.value.category,
        description: form.value.description,
        body: form.value.body,
      })
      ElMessage.success('保存成功')
    } else {
      await templateApi.create({
        name: form.value.name,
        category: form.value.category,
        description: form.value.description,
        body: form.value.body,
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

const onDelete = async (t: Template) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模板「${t.name}」吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  try {
    await templateApi.delete(t.id)
    ElMessage.success('删除成功')
    loadList()
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message))
  }
}

// 使用模板：创建草稿，跳转到编辑器
const onUse = async (t: Template) => {
  try {
    const newContent = await contentApi.create({
      title: t.name,
      body: t.body,
      tags: [],
      platform: 'all',
    })
    ElMessage.success('已基于模板创建内容，正在跳转编辑...')
    router.push(`/content/edit/${newContent.id}`)
  } catch (e: any) {
    ElMessage.error('创建失败: ' + (e.normalizedMessage || e.message))
  }
}

onMounted(loadList)
</script>

<style scoped>
.templates-page { padding: 0; }
.templates-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; color: #fff; }
.count-tag { margin-left: 4px; }
.filter-tabs { margin-bottom: 20px; }
.template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }
.template-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.3s ease;
}
.template-card:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(0, 212, 255, 0.2);
  transform: translateY(-2px);
}
.card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.tpl-name { font-size: 15px; font-weight: 600; color: #fff; line-height: 1.4; flex: 1; }
.tpl-desc { font-size: 13px; color: #a0a0b0; line-height: 1.5; }
.tpl-preview {
  font-size: 12px;
  color: #888;
  background: rgba(0, 0, 0, 0.3);
  padding: 10px 12px;
  border-radius: 6px;
  max-height: 120px;
  overflow: auto;
  font-family: monospace;
  line-height: 1.5;
  white-space: pre-wrap;
  margin: 0;
}
.card-actions { display: flex; gap: 6px; }
.card-actions .el-button { flex: 1; font-size: 12px; padding: 6px 8px; }
.empty-state, .loading-state { text-align: center; padding: 60px 20px; color: #666; }
.empty-state span { font-size: 48px; display: block; margin-bottom: 16px; }
.empty-state .hint { font-size: 13px; color: #444; margin-top: 8px; }
</style>
