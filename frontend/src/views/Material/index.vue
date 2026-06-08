<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/material">资源</router-link>
        <span>·</span>
        <span>素材库</span>
      </div>
      <h1 class="page-title">素材库</h1>
      <p class="page-subtitle">管理图片、音频、视频等可复用素材。支持标签分类、类型筛选。</p>

      <div class="header-actions">
        <el-button type="primary" @click="openCreate">添加素材</el-button>
      </div>
    </header>

    <el-tabs v-model="activeTab" @tab-change="filterByType" class="ds-tabs">
      <el-tab-pane v-for="t in MATERIAL_TYPES" :key="t.value" :label="t.label" :name="t.value" />
    </el-tabs>

    <div v-if="loading && materials.length === 0" class="ds-loading">
      <div class="spinner"></div>
      <div>正在加载素材…</div>
    </div>

    <div v-else-if="materials.length === 0" class="ds-empty">
      <div class="glyph">
        <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="6" y="6" width="20" height="20" rx="3" />
          <circle cx="12" cy="12" r="2" />
          <path d="M6 19l5-5 4 4 3-3 8 8" stroke-linejoin="round" />
        </svg>
      </div>
      <h4>还没有素材</h4>
      <p>从添加素材开始，或者把 AI 生成的图片保存到这里。</p>
      <el-button type="primary" @click="openCreate">添加第一个素材</el-button>
    </div>

    <div v-else class="ds-card-grid material-grid">
      <article v-for="item in materials" :key="item.id" class="ds-item-card material-card">
        <div class="thumb">
          <img v-if="item.type === 'image'" :src="item.path" :alt="item.name" loading="lazy" @error="onImgError" />
          <div v-else class="placeholder">
            <span class="ds-pill ds-pill--neutral">{{ getTypeLabel(item.type) }}</span>
          </div>
          <span class="type-badge ds-pill ds-pill--terracotta">{{ getTypeLabel(item.type) }}</span>
        </div>
        <div class="material-body">
          <h3 class="title" :title="item.name">{{ item.name }}</h3>
          <div class="path mono">{{ item.path }}</div>
          <div v-if="item.tags && item.tags.length" class="tags">
            <span v-for="t in item.tags" :key="t" class="ds-pill ds-pill--neutral">#{{ t }}</span>
          </div>
          <div v-if="item.description" class="desc">{{ item.description }}</div>
        </div>
        <div class="actions">
          <el-button size="small" @click="openEdit(item)">编辑</el-button>
          <el-button size="small" type="danger" text @click="onDelete(item)">删除</el-button>
        </div>
      </article>
    </div>

    <el-dialog v-model="showDialog" :title="isEdit ? '编辑素材' : '添加素材'" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="素材名称" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.type" style="width: 100%">
            <el-option v-for="t in MATERIAL_TYPES" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="路径 / URL" required>
          <el-input v-model="form.path" placeholder="本地路径或URL" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create default-first-option placeholder="输入标签后回车" style="width: 100%">
            <el-option label="封面" value="cover" />
            <el-option label="配图" value="inline" />
            <el-option label="背景" value="background" />
            <el-option label="logo" value="logo" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="素材说明..." />
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { materialApi, type Material } from '@/api/cms'
import { MATERIAL_TYPES, formatDateShort } from '@/constants'

const materials = ref<Material[]>([])
const loading = ref(false)
const saving = ref(false)
const activeTab = ref('all')
const showDialog = ref(false)
const isEdit = ref(false)
const form = ref({ id: '', name: '', type: 'image', path: '', tags: [] as string[], description: '' })

const getTypeLabel = (t: string) => MATERIAL_TYPES.find(m => m.value === t)?.label || t

const onImgError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}

const loadList = async () => {
  loading.value = true
  try {
    materials.value = await materialApi.list(activeTab.value === 'all' ? undefined : activeTab.value)
  } catch (e: any) { ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message)) }
  finally { loading.value = false }
}

const filterByType = () => loadList()

const openCreate = () => {
  isEdit.value = false
  form.value = { id: '', name: '', type: 'image', path: '', tags: [], description: '' }
  showDialog.value = true
}

const openEdit = (m: Material) => {
  isEdit.value = true
  form.value = {
    id: m.id, name: m.name, type: m.type, path: m.path,
    tags: [...(m.tags || [])], description: m.description || '',
  }
  showDialog.value = true
}

const onSave = async () => {
  if (!form.value.name.trim() || !form.value.path.trim()) {
    ElMessage.warning('请填写名称和路径'); return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await materialApi.update(form.value.id, form.value)
      ElMessage.success('保存成功')
    } else {
      await materialApi.create(form.value)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadList()
  } catch (e: any) { ElMessage.error('保存失败: ' + (e.normalizedMessage || e.message)) }
  finally { saving.value = false }
}

const onDelete = async (m: Material) => {
  try {
    await ElMessageBox.confirm(`确定要删除「${m.name}」吗？`, '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  try {
    await materialApi.delete(m.id)
    ElMessage.success('删除成功')
    loadList()
  } catch (e: any) { ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message)) }
}

onMounted(loadList)
</script>

<style scoped>
.ds-tabs { margin-bottom: 24px; }
.material-card { padding: 0; overflow: hidden; }
.material-card .thumb {
  position: relative; aspect-ratio: 4 / 3;
  background: var(--claude-parchment);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.material-card .thumb img { width: 100%; height: 100%; object-fit: cover; }
.material-card .thumb .placeholder {
  display: flex; align-items: center; justify-content: center;
  width: 100%; height: 100%;
  background: var(--claude-border-cream);
}
.material-card .type-badge {
  position: absolute; top: 12px; right: 12px;
}
.material-card .material-body { padding: 16px 20px 0; }
.material-card .title { font-size: 15px; }
.material-card .path {
  font-size: 12px; color: var(--claude-stone);
  margin-top: 4px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.material-card .desc {
  font-size: 13px; color: var(--claude-olive);
  margin-top: 8px; line-height: 1.5;
}
.material-card .actions {
  padding: 12px 20px; margin: 0;
}
</style>
