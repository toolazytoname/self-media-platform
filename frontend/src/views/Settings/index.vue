<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/settings">系统</router-link>
        <span>·</span>
        <span>设置</span>
      </div>
      <h1 class="page-title">设置</h1>
      <p class="page-subtitle">管理 AI 服务配置、查看系统信息。配置修改立即生效,无需重启。</p>
    </header>

    <!-- 顶部状态条:当前默认 provider + 配置总览 -->
    <section class="ds-card status-bar" v-if="providersList">
      <div class="status-row">
        <span class="ds-pill ds-pill--neutral">当前默认</span>
        <span class="ds-pill ds-pill--success">{{ defaultProviderLabel }}</span>
        <span class="caption">
          {{ providersReadyCount }} / 3 个 provider 已配置
        </span>
        <span class="grow"></span>
        <el-button size="small" @click="loadAll">刷新</el-button>
      </div>
    </section>

    <!-- 三张 provider 卡片(minimax / claude / openai) -->
    <section v-for="p in providersList?.providers || []" :key="p.name" class="ds-card provider-card">
      <header class="card-head">
        <h2 class="ds-card__title">{{ p.label }}</h2>
        <div class="card-status">
          <span v-if="p.is_default" class="ds-pill ds-pill--success">默认</span>
          <el-tag v-if="p.configured" type="success" effect="light" size="small">已配置</el-tag>
          <el-tag v-else type="info" effect="light" size="small">未配置</el-tag>
        </div>
      </header>

      <el-form :model="forms[p.name]" label-position="top" v-loading="loadingMap[p.name]">
        <el-form-item label="API Key">
          <el-input
            v-model="forms[p.name].api_key"
            :placeholder="`${p.key_prefix} 开头`"
            show-password
            clearable
          />
          <span v-if="p.api_key_masked" class="caption masked">当前: {{ p.api_key_masked }}</span>
        </el-form-item>

        <el-form-item label="Base URL">
          <el-input v-model="forms[p.name].base_url" :placeholder="p.default_base" />
        </el-form-item>

        <el-form-item label="默认模型">
          <el-select
            v-model="forms[p.name].model"
            filterable
            allow-create
            default-first-option
            :placeholder="p.default_model"
            style="width: 100%"
          >
            <el-option
              v-for="m in p.model_options.split(',')"
              :key="m"
              :label="m"
              :value="m"
            />
          </el-select>
          <span class="caption">可从下拉选,也可输入自定义 model 名</span>
        </el-form-item>

        <div class="form-actions">
          <el-button
            type="success"
            :loading="testingMap[p.name]"
            :disabled="!forms[p.name].api_key"
            @click="onTest(p.name)"
          >测试连接</el-button>
          <el-button
            type="primary"
            :loading="savingMap[p.name]"
            :disabled="!isDirty(p.name)"
            @click="onSave(p.name)"
          >保存</el-button>
          <el-button
            v-if="!p.is_default"
            :disabled="!p.configured"
            @click="onSetDefault(p.name)"
          >设为默认</el-button>
          <el-tag v-else type="success" effect="dark" size="small">当前默认</el-tag>
        </div>
      </el-form>
    </section>

    <!-- System info -->
    <section class="ds-card" style="margin-top: 32px">
      <h2 class="ds-card__title">系统信息</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="AI provider 数量">3 个(minimax / claude / openai)</el-descriptions-item>
        <el-descriptions-item label="视频生成模型">MiniMax-Hailuo-03(每日 3 次额度)</el-descriptions-item>
        <el-descriptions-item label="视频时长档位">3 / 6 / 10 秒</el-descriptions-item>
        <el-descriptions-item label="多平台分发">{{ supportedPlatforms.join(' · ') }}</el-descriptions-item>
      </el-descriptions>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { settingsApi, type ProviderInfo, type ProvidersListResponse } from '@/api/settings'
import { platformApi } from '@/api/platforms'

// 三家 provider 的当前表单状态(独立 dirty tracking)
interface Form { api_key: string; base_url: string; model: string }
const forms = reactive<Record<string, Form>>({
  minimax: { api_key: '', base_url: '', model: '' },
  claude: { api_key: '', base_url: '', model: '' },
  openai: { api_key: '', base_url: '', model: '' },
})

// 上次保存的快照,用于判断 dirty
const snapshots = reactive<Record<string, string>>({})

const loadingMap = reactive({ minimax: false, claude: false, openai: false })
const savingMap = reactive({ minimax: false, claude: false, openai: false })
const testingMap = reactive({ minimax: false, claude: false, openai: false })

const providersList = ref<ProvidersListResponse | null>(null)
const supportedPlatforms = ref<string[]>([])

const providersReadyCount = computed(() =>
  (providersList.value?.providers || []).filter(p => p.configured).length
)

const defaultProviderLabel = computed(() => {
  const p = (providersList.value?.providers || []).find(x => x.is_default)
  return p ? p.label : (providersList.value?.default || 'minimax')
})

const isDirty = (name: string): boolean => {
  const snap = snapshots[name] || ''
  const cur = `${forms[name].api_key}|${forms[name].base_url}|${forms[name].model}`
  return snap !== cur
}

const syncFormFromList = (list: ProvidersListResponse) => {
  for (const p of list.providers) {
    forms[p.name] = {
      api_key: '',  // 不预填(让用户主动改)
      base_url: p.base_url,
      model: p.model,
    }
    snapshots[p.name] = `|${p.base_url}|${p.model}`
  }
}

const loadAll = async () => {
  try {
    const list = await settingsApi.providersList()
    providersList.value = list
    syncFormFromList(list)
  } catch (e: any) {
    ElMessage.error('加载设置失败: ' + (e.normalizedMessage || e.message))
  }
}

const onTest = async (name: string) => {
  testingMap[name] = true
  try {
    const f = forms[name]
    const r = await settingsApi.test({
      provider: name,
      api_key: f.api_key,
      base_url: f.base_url,
      model: f.model || (providersList.value?.providers.find(p => p.name === name)?.default_model || ''),
    })
    if (r.success) {
      ElMessage.success(r.message + (r.response_preview ? ` · ${r.response_preview}` : ''))
    } else {
      ElMessage.error(r.message)
    }
  } catch (e: any) {
    ElMessage.error('测试失败: ' + (e.normalizedMessage || e.message))
  } finally {
    testingMap[name] = false
  }
}

const onSave = async (name: string) => {
  savingMap[name] = true
  try {
    const f = forms[name]
    await settingsApi.update({
      [name]: {
        api_key: f.api_key || undefined,
        base_url: f.base_url || undefined,
        model: f.model || undefined,
      },
    })
    ElMessage.success(`${name} 已保存`)
    await loadAll()
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.normalizedMessage || e.message))
  } finally {
    savingMap[name] = false
  }
}

const onSetDefault = async (name: string) => {
  try {
    await settingsApi.update({ default_provider: name })
    ElMessage.success(`已将 ${name} 设为默认 provider`)
    await loadAll()
  } catch (e: any) {
    ElMessage.error('设置默认失败: ' + (e.normalizedMessage || e.message))
  }
}

onMounted(async () => {
  await loadAll()
  // 拉 supported_platforms 给底部 System info
  try {
    const sauInfo = await platformApi.sauStatus()
    supportedPlatforms.value = sauInfo.supported_platforms
  } catch { /* silent */ }
})
</script>

<style scoped>
.status-bar {
  margin-bottom: 16px;
  padding: 12px 18px;
}
.status-row { display: flex; align-items: center; gap: 10px; }
.status-row .grow { flex: 1; }

.provider-card {
  margin-bottom: 16px;
}
.card-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.card-status { display: flex; gap: 8px; align-items: center; }

.masked {
  display: inline-block; margin-top: 4px;
  font-family: var(--font-mono, monospace); font-size: 12px;
}
.caption { color: var(--claude-stone); font-size: 12px; }

.form-actions { display: flex; gap: 8px; align-items: center; margin-top: 4px; }
</style>
