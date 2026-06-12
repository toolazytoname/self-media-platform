<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/platform">资源</router-link>
        <span>·</span>
        <span>平台账号</span>
      </div>
      <h1 class="page-title">平台账号</h1>
      <p class="page-subtitle">管理你发布到各平台用的账号。一个平台可以挂多个账号（主号 / 矩阵号）。</p>

      <div class="header-actions">
        <el-button type="primary" @click="openCreate">添加账号</el-button>
      </div>
    </header>

    <div v-if="loading && accounts.length === 0" class="ds-loading">
      <div class="spinner"></div>
      <div>正在加载账号…</div>
    </div>

    <div v-else-if="accounts.length === 0" class="ds-empty">
      <div class="glyph">
        <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="16" cy="16" r="12" />
          <path d="M4 16h24M16 4c4 4 4 20 0 24M16 4c-4 4-4 20 0 24" />
        </svg>
      </div>
      <h4>还没有平台账号</h4>
      <p>添加你的抖音、小红书、公众号等账号，开启多平台分发。</p>
      <el-button type="primary" @click="openCreate">添加第一个账号</el-button>
    </div>

    <div v-else class="ds-card-grid">
      <article v-for="item in accounts" :key="item.id" class="ds-item-card account-card">
        <div class="head">
          <h3 class="title">{{ getPlatformName(item.platform) }} · {{ item.name }}</h3>
          <span class="ds-status" :class="item.status === 'active' ? 'ds-status--success' : 'ds-status--neutral'">
            <span class="dot"></span>
            {{ item.status === 'active' ? '正常' : '已停用' }}
          </span>
        </div>
        <div class="meta">
          <span v-if="item.account_id" class="mono">{{ item.account_id }}</span>
        </div>
        <p v-if="item.description" class="body">{{ item.description }}</p>
        <div class="meta">
          <span class="caption">创建</span>
          <span class="mono">{{ formatDateShort(item.created_at) }}</span>
        </div>
        <div class="actions">
          <el-button size="small" @click="openEdit(item)">编辑</el-button>
          <el-button size="small" :type="item.status === 'active' ? 'warning' : 'success'" @click="toggleStatus(item)">
            {{ item.status === 'active' ? '停用' : '启用' }}
          </el-button>
          <el-button size="small" type="danger" text @click="onDelete(item)">删除</el-button>
        </div>
      </article>
    </div>

    <el-dialog v-model="showDialog" :title="isEdit ? '编辑账号' : '添加平台账号'" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="平台" required>
          <el-select v-model="form.platform" placeholder="选择平台" style="width: 100%" :disabled="isEdit">
            <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号名称" required>
          <el-input v-model="form.name" placeholder="如：主号 / 矩阵号-A" />
        </el-form-item>
        <el-form-item label="账号 ID">
          <el-input v-model="form.account_id" placeholder="平台的账号 ID（可选）" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="账号说明..." />
        </el-form-item>
        <el-form-item label="Cookie 路径(Phase 2,可选)">
          <el-input v-model="form.cookie_path" placeholder="留空则默认 storage/cookies/{name}.json" />
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
import { platformApi, type PlatformAccount } from '@/api/platforms'
import { PLATFORM_OPTIONS, getPlatformName, formatDateShort } from '@/constants'

const accounts = ref<PlatformAccount[]>([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const form = ref({ id: '', platform: '', name: '', account_id: '', description: '', cookie_path: '' })

const loadList = async () => {
  loading.value = true
  try { accounts.value = await platformApi.listAccounts() }
  catch (e: any) { ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message)) }
  finally { loading.value = false }
}

const openCreate = () => {
  isEdit.value = false
  form.value = { id: '', platform: '', name: '', account_id: '', description: '', cookie_path: '' }
  showDialog.value = true
}

const openEdit = (a: PlatformAccount) => {
  isEdit.value = true
  form.value = {
    id: a.id, platform: a.platform, name: a.name,
    account_id: a.account_id || '', description: a.description || '',
    cookie_path: a.cookie_path || '',
  }
  showDialog.value = true
}

const onSave = async () => {
  if (!form.value.platform || !form.value.name.trim()) {
    ElMessage.warning('请填写完整信息'); return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await platformApi.updateAccount(form.value.id, {
        name: form.value.name, description: form.value.description,
      })
      ElMessage.success('保存成功')
    } else {
      await platformApi.createAccount({
        platform: form.value.platform, name: form.value.name,
        account_id: form.value.account_id, description: form.value.description,
      })
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadList()
  } catch (e: any) { ElMessage.error('保存失败: ' + (e.normalizedMessage || e.message)) }
  finally { saving.value = false }
}

const toggleStatus = async (a: PlatformAccount) => {
  const newStatus = a.status === 'active' ? 'inactive' : 'active'
  try {
    await platformApi.updateAccount(a.id, { status: newStatus })
    ElMessage.success(newStatus === 'active' ? '已启用' : '已停用')
    loadList()
  } catch (e: any) { ElMessage.error('操作失败: ' + (e.normalizedMessage || e.message)) }
}

const onDelete = async (a: PlatformAccount) => {
  try {
    await ElMessageBox.confirm(`确定要删除「${a.name}」吗？`, '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  try {
    await platformApi.deleteAccount(a.id)
    ElMessage.success('删除成功')
    loadList()
  } catch (e: any) { ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message)) }
}

onMounted(loadList)
</script>
