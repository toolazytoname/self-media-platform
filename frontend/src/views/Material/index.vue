<template>
  <div class="material-page">
    <el-card class="material-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>🖼️</span>
            <span>素材库</span>
            <el-tag v-if="total > 0" size="small" type="info" class="count-tag">{{ total }} 个</el-tag>
          </div>
          <el-button type="primary" @click="openCreate">+ 添加素材</el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="filterByType" class="material-tabs">
        <el-tab-pane v-for="t in MATERIAL_TYPES" :key="t.value" :label="t.label" :name="t.value" />
      </el-tabs>

      <div v-if="loading && materials.length === 0" class="loading-state">加载中...</div>
      <div v-else-if="materials.length === 0" class="empty-state">
        <span class="empty-icon">📂</span>
        <p>暂无素材</p>
        <p class="empty-hint">点击上方按钮添加素材记录</p>
      </div>
      <el-row v-else :gutter="20" class="material-grid">
        <el-col v-for="item in materials" :key="item.id" :xs="24" :sm="12" :md="8" :lg="6">
          <div class="material-item">
            <div class="material-preview">
              <img v-if="item.type === 'image'" :src="item.path" :alt="item.name"
                   @error="onImgError($event)" />
              <div v-else-if="item.type === 'video'" class="placeholder">
                <span>🎬</span>
                <small>视频</small>
              </div>
              <div v-else-if="item.type === 'audio'" class="placeholder">
                <span>🎵</span>
                <small>音频</small>
              </div>
              <div v-else class="placeholder">
                <span>📄</span>
                <small>文本</small>
              </div>
              <div class="type-badge">{{ getTypeLabel(item.type) }}</div>
            </div>
            <div class="material-info">
              <div class="material-name" :title="item.name">{{ item.name }}</div>
              <div class="material-path" :title="item.path">{{ item.path }}</div>
              <div v-if="item.tags && item.tags.length" class="material-tags">
                <el-tag v-for="tag in item.tags" :key="tag" size="small" class="tag">
                  {{ tag }}
                </el-tag>
              </div>
              <div class="material-actions">
                <el-button size="small" @click="openEdit(item)">编辑</el-button>
                <el-button size="small" type="danger" @click="onDelete(item)">删除</el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑素材' : '添加素材'" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="素材名称" required>
          <el-input v-model="form.name" placeholder="例如：封面图-A" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-radio-group v-model="form.type">
            <el-radio-button v-for="t in MATERIAL_TYPES.filter(m=>m.value!=='all')" :key="t.value" :value="t.value">
              {{ t.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="路径 / URL" required>
          <el-input v-model="form.path" placeholder="本地路径或URL，例如：/uploads/cover.png 或 https://..." />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create
                     default-first-option
                     placeholder="输入标签后回车" style="width: 100%">
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { materialApi, type Material } from '@/api/cms'
import { MATERIAL_TYPES, formatDateShort } from '@/constants'

const materials = ref<Material[]>([])
const loading = ref(false)
const saving = ref(false)
const activeTab = ref('all')
const showDialog = ref(false)
const isEdit = ref(false)
const total = computed(() => materials.value.length)
const form = ref({
  id: '',
  name: '',
  type: 'image',
  path: '',
  tags: [] as string[],
  description: '',
})

const getTypeLabel = (t: string) => MATERIAL_TYPES.find(m => m.value === t)?.label || t

const onImgError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
  const parent = img.parentElement
  if (parent && !parent.querySelector('.fallback')) {
    const fallback = document.createElement('div')
    fallback.className = 'placeholder fallback'
    fallback.innerHTML = '<span>🖼️</span><small>图片加载失败</small>'
    parent.appendChild(fallback)
  }
}

const loadList = async (type?: string) => {
  loading.value = true
  try {
    materials.value = await materialApi.list(type === 'all' ? undefined : type)
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message))
  } finally {
    loading.value = false
  }
}

const filterByType = (t: any) => loadList(typeof t === 'string' ? t : t?.props?.name)

const openCreate = () => {
  isEdit.value = false
  form.value = { id: '', name: '', type: 'image', path: '', tags: [], description: '' }
  showDialog.value = true
}

const openEdit = (m: Material) => {
  isEdit.value = true
  form.value = {
    id: m.id,
    name: m.name,
    type: m.type,
    path: m.path,
    tags: [...(m.tags || [])],
    description: m.description || '',
  }
  showDialog.value = true
}

const onSave = async () => {
  if (!form.value.name.trim() || !form.value.path.trim()) {
    ElMessage.warning('请填写名称和路径')
    return
  }
  saving.value = true
  try {
    const data = {
      name: form.value.name,
      type: form.value.type,
      path: form.value.path,
      tags: form.value.tags,
      description: form.value.description,
    }
    if (isEdit.value) {
      await materialApi.update(form.value.id, data)
      ElMessage.success('保存成功')
    } else {
      await materialApi.create(data)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadList(activeTab.value)
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.normalizedMessage || e.message))
  } finally {
    saving.value = false
  }
}

const onDelete = async (m: Material) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除素材「${m.name}」吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  try {
    await materialApi.delete(m.id)
    ElMessage.success('删除成功')
    loadList(activeTab.value)
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message))
  }
}

onMounted(() => loadList('all'))
</script>

<style scoped>
.material-page { padding: 0; }
.material-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; color: #fff; }
.count-tag { margin-left: 4px; }
.material-grid { margin-top: 20px; }
.material-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
}
.material-item:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.3);
}
.material-preview {
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  position: relative;
}
.material-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
}
.placeholder {
  font-size: 40px;
  opacity: 0.5;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.placeholder small {
  font-size: 12px;
  opacity: 0.7;
}
.type-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
}
.material-info { padding: 12px; display: flex; flex-direction: column; gap: 6px; }
.material-name { font-size: 14px; font-weight: 500; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.material-path { font-size: 11px; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.material-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.tag { background: rgba(0, 212, 255, 0.1); border: none; color: #00d4ff; font-size: 10px; }
.material-actions { display: flex; gap: 6px; margin-top: 6px; }
.material-actions .el-button { flex: 1; font-size: 12px; padding: 4px; }
.empty-state, .loading-state { text-align: center; padding: 60px 20px; color: #666; }
.empty-icon { font-size: 60px; opacity: 0.5; display: block; margin-bottom: 12px; }
.empty-hint { font-size: 12px; color: #444; margin-top: 4px; }
</style>
