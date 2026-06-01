<template>
  <div class="platform-page">
    <el-card class="platform-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>🌐</span>
            <span>平台管理</span>
          </div>
          <el-button type="primary" @click="showDialog = true">
            + 添加账号
          </el-button>
        </div>
      </template>

      <div v-if="accounts.length === 0" class="empty-state">
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
            <div class="account-meta">
              <span class="status-badge" :class="item.status">{{ item.status === 'active' ? '正常' : '异常' }}</span>
              <span class="date">{{ formatDate(item.created_at) }}</span>
            </div>
          </div>
          <el-button size="small" type="danger" text @click="deleteAccount(item.id)" class="delete-btn">
            删除
          </el-button>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="showDialog" title="添加平台账号" width="450px" class="dialog">
      <el-form :model="form" label-position="top">
        <el-form-item label="平台">
          <el-select v-model="form.platform" placeholder="选择平台" style="width: 100%">
            <el-option label="抖音" value="douyin" />
            <el-option label="B站" value="bilibili" />
            <el-option label="YouTube" value="youtube" />
            <el-option label="小红书" value="xiaohongshu" />
            <el-option label="头条号" value="toutiao" />
            <el-option label="公众号" value="wechat" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号名称">
          <el-input v-model="form.name" placeholder="输入账号名称或昵称..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="addAccount">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const accounts = ref<any[]>([])
const showDialog = ref(false)
const form = ref({
  platform: '',
  name: ''
})

const platformMap: Record<string, { name: string; icon: string }> = {
  douyin: { name: '抖音', icon: '🎵' },
  bilibili: { name: 'B站', icon: '📺' },
  youtube: { name: 'YouTube', icon: '▶️' },
  xiaohongshu: { name: '小红书', icon: '📕' },
  toutiao: { name: '头条号', icon: '📰' },
  wechat: { name: '公众号', icon: '💬' }
}

const getPlatformName = (key: string) => platformMap[key]?.name || key
const getPlatformIcon = (key: string) => platformMap[key]?.icon || '🌐'

const fetchAccounts = async () => {
  try {
    const res = await axios.get('/api/platforms/accounts')
    accounts.value = res.data
  } catch (error) {
    console.error('Failed to fetch accounts:', error)
  }
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()}`
}

const addAccount = async () => {
  if (!form.value.platform || !form.value.name) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    await axios.post('/api/platforms/accounts', {
      platform: form.value.platform,
      name: form.value.name
    })
    ElMessage.success('添加成功')
    showDialog.value = false
    fetchAccounts()
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

const deleteAccount = async (id: string) => {
  try {
    await axios.delete(`/api/platforms/accounts/${id}`)
    ElMessage.success('删除成功')
    fetchAccounts()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

onMounted(fetchAccounts)
</script>

<style scoped>
.platform-page {
  padding: 0;
}

.platform-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-state span {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.empty-state .hint {
  font-size: 13px;
  color: #444;
  margin-top: 8px;
}

.account-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

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
  position: relative;
}

.account-card:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(0, 212, 255, 0.2);
  transform: translateY(-2px);
}

.account-icon {
  font-size: 40px;
}

.account-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.account-platform {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.account-name {
  font-size: 13px;
  color: #aaa;
}

.account-meta {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-badge.active {
  background: rgba(0, 212, 100, 0.15);
  color: #00dc64;
}

.status-badge.inactive {
  background: rgba(255, 71, 87, 0.15);
  color: #ff4757;
}

.date {
  font-size: 11px;
  color: #666;
}

.delete-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.account-card:hover .delete-btn {
  opacity: 1;
}

.dialog :deep(.el-dialog) {
  background: #1a1a2e;
  border-radius: 16px;
}
</style>