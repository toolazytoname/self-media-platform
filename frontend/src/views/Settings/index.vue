<template>
  <div class="settings-page">
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>⚙️</span>
            <span>系统设置</span>
          </div>
        </div>
      </template>

      <el-form :model="settings" label-position="top" class="settings-form">
        <!-- AI 设置 -->
        <div class="section-title">
          <span>🤖 AI 配置</span>
        </div>

        <el-form-item label="API 密钥">
          <el-input
            v-model="settings.minimax_api_key"
            type="password"
            show-password
            placeholder="sk-cp-xxxxx"
          />
        </el-form-item>

        <el-form-item label="API 地址">
          <el-input
            v-model="settings.minimax_base_url"
            placeholder="https://api.minimaxi.com/v1"
          />
        </el-form-item>

        <el-form-item label="模型名称">
          <el-select v-model="settings.model_name" style="width: 100%">
            <el-option label="MiniMax-M3" value="MiniMax-M3" />
            <el-option label="MiniMax-M4" value="MiniMax-M4" />
            <el-option label="MiniMax-Text-01" value="MiniMax-Text-01" />
            <el-option label="abab6.5s-chat" value="abab6.5s-chat" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveSettings" :loading="saving">
            💾 保存配置
          </el-button>
          <el-button @click="testConnection" :loading="testing" class="test-btn">
            🧪 测试连接
          </el-button>
        </el-form-item>

        <!-- 测试结果 -->
        <div v-if="testResult" :class="['test-result', testResult.success ? 'success' : 'error']">
          <span v-if="testResult.success">✅ {{ testResult.message }}</span>
          <span v-else>❌ {{ testResult.message }}</span>
        </div>

        <!-- 平台账号状态 -->
        <div class="section-title" style="margin-top: 32px">
          <span>🌐 平台账号状态</span>
        </div>

        <div class="platforms-status">
          <div
            v-for="platform in platforms"
            :key="platform.key"
            class="platform-status-item"
          >
            <span class="platform-icon">{{ platform.icon }}</span>
            <span class="platform-name">{{ platform.name }}</span>
            <el-tag :type="platform.connected ? 'success' : 'info'" size="small">
              {{ platform.connected ? '已配置' : '待配置' }}
            </el-tag>
          </div>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const settings = ref({
  minimax_api_key: '',
  minimax_base_url: 'https://api.minimaxi.com/v1',
  model_name: 'MiniMax-M3'
})

const saving = ref(false)
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)

const platforms = ref([
  { key: 'douyin', name: '抖音', icon: '🎵', connected: false },
  { key: 'bilibili', name: 'B站', icon: '📺', connected: false },
  { key: 'xiaohongshu', name: '小红书', icon: '📕', connected: false },
  { key: 'youtube', name: 'YouTube', icon: '▶️', connected: false },
  { key: 'toutiao', name: '头条号', icon: '📰', connected: false },
  { key: 'wechat', name: '公众号', icon: '💬', connected: false }
])

const loadSettings = async () => {
  try {
    const res = await axios.get('/api/config')
    if (res.data) {
      settings.value = {
        minimax_api_key: '',
        minimax_base_url: res.data.minimax_base_url || 'https://api.minimaxi.com/v1',
        model_name: res.data.model_name || 'MiniMax-M3'
      }
    }
  } catch (error) {
    console.log('加载默认配置')
  }
}

const loadPlatforms = async () => {
  try {
    const res = await axios.get('/api/platforms/accounts')
    const connectedPlatforms = new Set(res.data.map((a: any) => a.platform))
    platforms.value = platforms.value.map(p => ({
      ...p,
      connected: connectedPlatforms.has(p.key)
    }))
  } catch (error) {
    console.log('加载平台状态失败')
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await axios.post('/api/config', settings.value)
    // 保存到环境变量并更新运行时配置
    const client_res = await axios.post('/api/config/test', {
      api_key: settings.value.minimax_api_key,
      base_url: settings.value.minimax_base_url,
      model: settings.value.model_name
    })
    if (client_res.data.success) {
      ElMessage.success('配置已保存并生效')
    } else {
      ElMessage.warning('配置已保存但测试失败')
    }
  } catch (error) {
    // 保存到 localStorage 作为备选
    localStorage.setItem('ai_settings', JSON.stringify(settings.value))
    ElMessage.success('配置已保存到本地')
  } finally {
    saving.value = false
  }
}

const testConnection = async () => {
  testing.value = true
  testResult.value = null

  try {
    const res = await axios.post('/api/config/test', {
      api_key: settings.value.minimax_api_key,
      base_url: settings.value.minimax_base_url,
      model: settings.value.model_name
    })
    
    if (res.data.success) {
      testResult.value = {
        success: true,
        message: res.data.message || '连接成功！AI 功能可以正常使用'
      }
      ElMessage.success('连接测试成功')
    } else {
      testResult.value = {
        success: false,
        message: res.data.message || '连接失败'
      }
    }
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: error.response?.data?.message || error.message || '连接失败，请检查配置'
    }
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadSettings()
  loadPlatforms()
})
</script>

<style scoped>
.settings-page {
  padding: 0;
}

.settings-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  max-width: 600px;
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

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.test-btn {
  margin-left: 12px;
  background: rgba(102, 126, 234, 0.2);
  border-color: rgba(102, 126, 234, 0.4);
  color: #a78bfa;
}

.test-btn:hover {
  background: rgba(102, 126, 234, 0.3);
  border-color: #a78bfa;
}

.test-result {
  margin-top: 16px;
  padding: 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.test-result.success {
  background: rgba(0, 212, 100, 0.1);
  border: 1px solid rgba(0, 212, 100, 0.3);
  color: #00dc64;
}

.test-result.error {
  background: rgba(255, 71, 87, 0.1);
  border: 1px solid rgba(255, 71, 87, 0.3);
  color: #ff4757;
}

.platforms-status {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.platform-status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
}

.platform-icon {
  font-size: 20px;
}

.platform-name {
  flex: 1;
  font-size: 13px;
  color: #e0e0e0;
}
</style>