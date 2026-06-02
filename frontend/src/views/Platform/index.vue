<template>
  <div class="platform-page">
    <el-card class="platform-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>🌐</span>
            <span>平台账号</span>
            <el-tag v-if="total > 0" size="small" type="info" class="count-tag">{{ total }} 个</el-tag>
          </div>
          <el-button type="primary" @click="openCreate">+ 添加账号</el-button>
        </div>
      </template>

      <div v-if="loading && accounts.length === 0" class="loading-state">加载中...</div>
      <div v-else-if="accounts.length === 0" class="empty-state">
        <span>🌐</span>
        <p>暂无平台账号</p>
        <p class="hint">点击上方按钮添加第一个平台账号</p>
      </div>
      <div v-else class="account-grid">
        <div v-for="item in accounts" :key="item.id" class="account-card">
          <div class="account-icon">{{ getPlatformIcon(item.platform) }}</div>
          <div class="account-info">
            <div class="account-platform">{{ getPlatformName(item.platform) }}</div>
            <div class="account-name">{{ item.name }}</div>
            <div v-if="item.account_id" class="account-id">ID: {{ item.account_id }}</div>
            <div v-if="item.description" class="account-desc">{{ item.description }}</div>
            <div class="account-meta">
              <span class="status-badge" :class="item.status">{{ item.status === 'active' ? '正常' : '已停用' }}</span>
              <span class="date">{{ formatDateShort(item.created_at) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <el-button size="small" @click="openEdit(item)">编辑</el-button>
            <el-button size="small" :type="item.status === 'active' ? 'warning' : 'success'"
                       @click="toggleStatus(item)">
              {{ item.status === 'active' ? '停用' : '启用' }}
            </el-button>
            <el-button size="small" type="danger" @click="onDelete(item)">删除</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="showDialog" :title="isEdit ? '编辑账号' : '添加平台账号'" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="平台" required>
          <el-select v-model="form.platform" placeholder="选择平台" style="width: 100%" :disabled="isEdit">
            <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号名称" required>
          <el-input v-model="form.name" placeholder="输入账号名称或昵称..." maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="平台账号 ID">
          <el-input v-model="form.account_id" placeholder="可选：平台上的账号 ID" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="账号备注..." />
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
import { platformApi, type PlatformAccount } from '@/api/platforms'
import { PLATFORM_OPTIONS, getPlatformName, getPlatformIcon, formatDateShort } from '@/constants'

const accounts = ref<PlatformAccount[]>([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const total = computed(() => accounts.value.length)

const form = ref({
  id: '',
  platform: '',
  name: '',
  account_id: '',
  description: '',
})

const loadList = async () => {
  loading.value = true
  try {
    accounts.value = await platformApi.listAccounts()
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message))
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  isEdit.value = false
  form.value = { id: '', platform: '', name: '', account_id: '', description: '' }
  showDialog.value = true
}

const openEdit = (a: PlatformAccount) => {
  isEdit.value = true
  form.value = {
    id: a.id,
    platform: a.platform,
    name: a.name,
    account_id: a.account_id || '',
    description: a.description || '',
  }
  showDialog.value = true
}

const onSave = async () => {
  if (!form.value.platform || !form.value.name.trim()) {
    ElMessage.warning('请填写完整信息')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await platformApi.updateAccount(form.value.id, {
        name: form.value.name,
        description: form.value.description,
      })
      ElMessage.success('保存成功')
    } else {
      await platformApi.addAccount({
        platform: form.value.platform,
        name: form.value.name,
        account_id: form.value.account_id || undefined,
        description: form.value.description,
      })
      ElMessage.success('添加成功')
    }
    showDialog.value = false
    loadList()
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.normalizedMessage || e.message))
  } finally {
    saving.value = false
  }
}

const toggleStatus = async (a: PlatformAccount) => {
  const newStatus = a.status === 'active' ? 'inactive' : 'active'
  try {
    await platformApi.updateAccount(a.id, { status: newStatus })
    ElMessage.success(newStatus === 'active' ? '已启用' : '已停用')
    loadList()
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e.normalizedMessage || e.message))
  }
}

const onDelete = async (a: PlatformAccount) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除账号「${a.name}」吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  try {
    await platformApi.deleteAccount(a.id)
    ElMessage.success('删除成功')
    loadList()
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e.normalizedMessage || e.message))
  }
}

onMounted(loadList)
</script>

<style scoped>
.platform-page { padding: 0; }
.platform-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; color: #fff; }
.count-tag { margin-left: 4px; }
.empty-state, .loading-state { text-align: center; padding: 60px 20px; color: #666; }
.empty-state span { font-size: 48px; display: block; margin-bottom: 16px; }
.empty-state .hint { font-size: 13px; color: #444; margin-top: 8px; }
.account-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.account-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
  transition: all 0.3s ease;
}
.account-card:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(0, 212, 255, 0.2);
  transform: translateY(-2px);
}
.account-icon { font-size: 40px; }
.account-info { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.account-platform { font-size: 14px; font-weight: 600; color: #fff; }
.account-name { font-size: 13px; color: #aaa; }
.account-id { font-size: 11px; color: #666; font-family: monospace; }
.account-desc { font-size: 12px; color: #888; line-height: 1.4; margin-top: 4px; }
.account-meta { display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 4px; }
.status-badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; }
.status-badge.active { background: rgba(0, 212, 100, 0.15); color: #00dc64; }
.status-badge.inactive { background: rgba(255, 159, 67, 0.15); color: #ff9f43; }
.date { font-size: 11px; color: #666; }
.card-actions { display: flex; gap: 6px; width: 100%; }
.card-actions .el-button { flex: 1; font-size: 12px; padding: 6px 4px; }
</style>
