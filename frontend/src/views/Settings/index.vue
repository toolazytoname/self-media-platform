<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/settings">系统</router-link>
        <span>·</span>
        <span>设置</span>
      </div>
      <h1 class="page-title">设置</h1>
      <p class="page-subtitle">管理 AI 服务配置、查看系统信息。配置修改立即生效，无需重启。</p>
    </header>

    <!-- AI Service config card -->
    <section class="ds-card">
      <h2 class="ds-card__title">AI 服务配置</h2>
      <p class="ds-card__lede">使用 MiniMax 系列模型（文本 / 图像 / 视频 / 语音）。</p>

      <div class="ds-notice">
        <div>
          <p><strong>申请 API Key：</strong><a href="https://platform.minimaxi.com" target="_blank" rel="noopener">platform.minimaxi.com</a></p>
          <p>配置完成后点击「测试连接」验证，AI 生成功能会立即可用。</p>
        </div>
      </div>

      <el-form :model="form" label-position="top" v-loading="loading" class="settings-form">
        <el-form-item label="API Key">
          <el-input v-model="form.minimax_api_key" placeholder="输入 MiniMax API Key" show-password clearable />
        </el-form-item>

        <el-form-item label="Base URL">
          <el-input v-model="form.minimax_base_url" placeholder="例如：https://api.minimaxi.com/v1" />
        </el-form-item>

        <el-form-item label="模型名称">
          <el-select v-model="form.model_name" filterable allow-create default-first-option placeholder="选择或输入模型" style="width: 100%">
            <el-option label="MiniMax-M3" value="MiniMax-M3" />
            <el-option label="MiniMax-Text-01" value="MiniMax-Text-01" />
            <el-option label="abab6.5s-chat" value="abab6.5s-chat" />
            <el-option label="abab6.5-chat" value="abab6.5-chat" />
          </el-select>
        </el-form-item>

        <div class="form-actions">
          <el-button @click="loadSettings">刷新</el-button>
          <el-button type="success" :loading="testing" :disabled="!form.minimax_api_key" @click="onTest">测试连接</el-button>
          <el-button type="primary" :loading="saving" @click="onSave">保存配置</el-button>
        </div>
      </el-form>

      <el-divider />

      <div class="status-row">
        <span class="caption">当前状态</span>
        <el-tag v-if="settings.configured" type="success" effect="light" round>已配置 · {{ settings.model_name }}</el-tag>
        <el-tag v-else type="warning" effect="light" round>未配置</el-tag>
        <span v-if="settings.minimax_api_key" class="ds-pill ds-pill--neutral">Key · {{ settings.minimax_api_key }}</span>
      </div>
    </section>

    <!-- System info -->
    <section class="ds-card" style="margin-top: 32px">
      <h2 class="ds-card__title">系统信息</h2>
      <p class="ds-card__lede">当前部署的基础信息。</p>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="平台版本">v1.0.0</el-descriptions-item>
        <el-descriptions-item label="后端">FastAPI + Pydantic v2</el-descriptions-item>
        <el-descriptions-item label="前端">Vue 3 + TypeScript + Element Plus</el-descriptions-item>
        <el-descriptions-item label="AI 服务">MiniMax (MiniMax-M3)</el-descriptions-item>
        <el-descriptions-item label="存储">内存 (生产可切 PostgreSQL)</el-descriptions-item>
        <el-descriptions-item label="设计系统">Apple (chrome) + Claude (body)</el-descriptions-item>
      </el-descriptions>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { settingsApi, type Settings } from '@/api/settings'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)

const form = reactive({
  minimax_api_key: '',
  minimax_base_url: 'https://api.minimaxi.com/v1',
  model_name: 'MiniMax-M3',
})

const settings = ref<Settings>({
  configured: false,
  minimax_api_key: '',
  minimax_base_url: '',
  model_name: '',
})

const loadSettings = async () => {
  loading.value = true
  try {
    const s = await settingsApi.get()
    settings.value = s
    form.minimax_api_key = s.minimax_api_key || ''
    form.minimax_base_url = s.minimax_base_url || 'https://api.minimaxi.com/v1'
    form.model_name = s.model_name || 'MiniMax-M3'
  } catch (e: any) {
    ElMessage.error('加载配置失败: ' + (e.normalizedMessage || e.message))
  } finally {
    loading.value = false
  }
}

const onSave = async () => {
  saving.value = true
  try {
    await settingsApi.update({
      minimax_api_key: form.minimax_api_key,
      minimax_base_url: form.minimax_base_url,
      model_name: form.model_name,
    })
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
      minimax_api_key: form.minimax_api_key,
      minimax_base_url: form.minimax_base_url,
      model_name: form.model_name,
    })
    if (res.ok) ElMessage.success('连接成功：' + (res.message || ''))
    else ElMessage.error('连接失败：' + (res.message || '未知错误'))
  } catch (e: any) {
    ElMessage.error('测试失败: ' + (e.normalizedMessage || e.message))
  } finally {
    testing.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.status-row {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
</style>
