<template>
  <div class="settings-page">
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>⚙️</span>
            <span>AI 服务配置</span>
          </div>
          <el-button @click="loadSettings" :icon="undefined">🔄 重新加载</el-button>
        </div>
      </template>

      <el-alert type="info" :closable="false" class="info-alert">
        <p>📌 申请 API Key：<a href="https://platform.minimaxi.com" target="_blank" class="link">https://platform.minimaxi.com</a></p>
        <p>配置完成后点击"测试连接"验证，AI 生成功能会立即可用</p>
      </el-alert>

      <el-form :model="form" label-position="top" v-loading="loading">
        <el-form-item label="API Key">
          <el-input
            v-model="form.minimax_api_key"
            placeholder="输入 MiniMax API Key"
            show-password
            clearable
          />
          <div class="hint">
            <span v-if="form.minimax_api_key">当前值（已脱敏显示在状态栏）</span>
            <span v-else class="warn">⚠️ 未配置</span>
          </div>
        </el-form-item>

        <el-form-item label="Base URL">
          <el-input v-model="form.minimax_base_url" placeholder="例如：https://api.minimaxi.com/v1" />
        </el-form-item>

        <el-form-item label="模型名称">
          <el-select v-model="form.model_name" filterable allow-create
                     default-first-option
                     placeholder="选择或输入模型" style="width: 100%">
            <el-option label="MiniMax-M3" value="MiniMax-M3" />
            <el-option label="MiniMax-Text-01" value="MiniMax-Text-01" />
            <el-option label="abab6.5s-chat" value="abab6.5s-chat" />
            <el-option label="abab6.5-chat" value="abab6.5-chat" />
          </el-select>
        </el-form-item>

        <div class="form-actions">
          <el-button type="success" @click="onTest" :loading="testing" :disabled="!form.minimax_api_key">
            🧪 测试连接
          </el-button>
          <el-button type="primary" @click="onSave" :loading="saving">
            💾 保存配置
          </el-button>
        </div>
      </el-form>

      <el-divider />

      <div class="status-bar">
        <span class="status-label">当前状态：</span>
        <el-tag v-if="settings.configured" type="success" size="small">✅ 已配置 ({{ settings.model_name }})</el-tag>
        <el-tag v-else type="warning" size="small">⚠️ 未配置</el-tag>
        <span v-if="settings.minimax_api_key" class="key-display">
          Key: <code>{{ settings.minimax_api_key }}</code>
        </span>
      </div>
    </el-card>

    <!-- 系统信息卡 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-title"><span>ℹ️</span><span>系统信息</span></div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="平台版本">v1.0.0</el-descriptions-item>
        <el-descriptions-item label="后端 API">FastAPI + Pydantic v2</el-descriptions-item>
        <el-descriptions-item label="前端框架">Vue 3 + TypeScript + Element Plus</el-descriptions-item>
        <el-descriptions-item label="AI 服务">MiniMax (MiniMax-M3)</el-descriptions-item>
        <el-descriptions-item label="存储">内存 (生产环境可切 PostgreSQL)</el-descriptions-item>
        <el-descriptions-item label="支持平台">{{ supportedPlatformsText }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { settingsApi, type Settings } from '@/api/settings'
import { PLATFORM_OPTIONS, getPlatformName } from '@/constants'

const settings = ref<Settings>({
  minimax_api_key: '',
  minimax_base_url: 'https://api.minimaxi.com/v1',
  model_name: 'MiniMax-M3',
  configured: false,
})

const form = ref({
  minimax_api_key: '',
  minimax_base_url: 'https://api.minimaxi.com/v1',
  model_name: 'MiniMax-M3',
})

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)

const supportedPlatformsText = computed(() =>
  PLATFORM_OPTIONS.map(p => p.label).join(' / ')
)

const loadSettings = async () => {
  loading.value = true
  try {
    settings.value = await settingsApi.get()
    form.value = {
      minimax_api_key: settings.value.minimax_api_key, // 已脱敏
      minimax_base_url: settings.value.minimax_base_url,
      model_name: settings.value.model_name,
    }
  } catch (e: any) {
    ElMessage.error('加载配置失败: ' + (e.normalizedMessage || e.message))
  } finally {
    loading.value = false
  }
}

const onSave = async () => {
  if (!form.value.minimax_api_key) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  saving.value = true
  try {
    await settingsApi.update(form.value)
    ElMessage.success('保存成功')
    loadSettings()
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.normalizedMessage || e.message))
  } finally {
    saving.value = false
  }
}

const onTest = async () => {
  testing.value = true
  try {
    const res = await settingsApi.test({
      api_key: form.value.minimax_api_key,
      base_url: form.value.minimax_base_url,
      model: form.value.model_name,
    })
    if (res.success) {
      ElMessageBox.alert(res.message, '✅ 连接成功', { type: 'success' })
    } else {
      ElMessageBox.alert(res.message, '❌ 连接失败', { type: 'error' })
    }
  } catch (e: any) {
    ElMessage.error('测试失败: ' + (e.normalizedMessage || e.message))
  } finally {
    testing.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.settings-page { padding: 0; display: flex; flex-direction: column; gap: 20px; max-width: 800px; margin: 0 auto; }
.settings-card, .info-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; color: #fff; }
.info-alert { margin-bottom: 20px; }
.info-alert p { margin: 4px 0; }
.link { color: #00d4ff; text-decoration: none; }
.link:hover { text-decoration: underline; }
.hint { font-size: 12px; color: #888; margin-top: 6px; }
.hint .warn { color: #ff9f43; }
.form-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; }
.status-bar {
  display: flex; align-items: center; gap: 12px; padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}
.status-label { font-size: 14px; color: #a0a0b0; }
.key-display { font-size: 12px; color: #888; margin-left: auto; }
.key-display code { background: rgba(0, 0, 0, 0.3); padding: 2px 6px; border-radius: 4px; font-family: monospace; }
:deep(.el-descriptions__label) { color: #a0a0b0; }
:deep(.el-descriptions__content) { color: #fff; }
</style>
