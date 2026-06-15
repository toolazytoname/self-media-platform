<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/publish-records">工作流</router-link>
        <span>·</span>
        <span>发布记录</span>
      </div>
      <h1 class="page-title">发布记录</h1>
      <p class="page-subtitle">查看内容到各平台的发布历史。失败的任务会显示原因，可以重试。</p>

      <div class="header-actions">
        <el-button type="primary" @click="openPublishDialog">发布视频</el-button>
        <el-button @click="onRunDue" :loading="running">执行到期任务</el-button>
        <el-button @click="loadList">刷新</el-button>
      </div>
    </header>

    <div class="ds-filter-bar">
      <el-select v-model="filterStatus" placeholder="状态" clearable @change="loadList" style="width: 160px">
        <el-option v-for="s in PUBLISH_STATUSES" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filterPlatform" placeholder="平台" clearable @change="loadList" style="width: 180px">
        <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
      </el-select>
      <div style="flex: 1"></div>
      <span class="caption">共 {{ total }} 条</span>
    </div>

    <div v-if="loading && list.length === 0" class="ds-loading">
      <div class="spinner"></div>
      <div>正在加载发布记录…</div>
    </div>

    <div v-else-if="filteredList.length === 0" class="ds-empty">
      <div class="glyph">
        <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M8 22V10h16v12M4 22h24M12 14h8M12 18h6" stroke-linecap="round" />
        </svg>
      </div>
      <h4>还没有发布记录</h4>
      <p>从内容详情页发布内容后，任务会出现在这里。</p>
    </div>

    <el-table v-else :data="filteredList" v-loading="loading" stripe class="ds-table">
      <el-table-column label="ID" width="200">
        <template #default="{ row }">
          <code class="mono id-code">{{ row.publish_id.slice(0, 8) }}…</code>
        </template>
      </el-table-column>
      <el-table-column label="内容" prop="content_title" min-width="200" show-overflow-tooltip />
      <el-table-column label="平台" width="140">
        <template #default="{ row }">
          <span class="ds-pill ds-pill--neutral">{{ getPlatformName(row.platform) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <span class="ds-status" :class="statusClass(row.status)">
            <span class="dot"></span>
            {{ statusLabel(row.status) || getStatusMeta(PUBLISH_STATUSES, row.status).label }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="计划时间" width="180">
        <template #default="{ row }">
          <span class="mono">{{ formatDate(row.scheduled_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="结果" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.error_message" class="ds-pill ds-pill--warning">{{ row.error_message }}</span>
          <span v-else-if="row.url" class="ds-pill ds-pill--success">
            <a :href="row.url" target="_blank" rel="noopener">查看</a>
          </span>
          <span v-else-if="row.platform === 'wechat' && row.freepublish_status != null" class="ds-pill ds-pill--neutral">
            freepublish={{ row.freepublish_status }}
          </span>
          <span v-else class="caption">—</span>
        </template>
      </el-table-column>
    </el-table>

    <!-- Phase 2: 立即发布视频弹窗 -->
    <el-dialog v-model="showPublishDialog" title="发布视频到平台" width="560">
      <el-form :model="publishForm" label-position="top">
        <el-form-item label="内容">
          <el-select v-model="publishForm.content_id" filterable placeholder="选择要发布的内容" style="width: 100%"
                     @change="onContentChange">
            <el-option v-for="c in contents" :key="c.id" :label="c.title" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="视频">
          <el-select v-model="publishForm.video_id" filterable placeholder="选择要发布的视频" style="width: 100%">
            <el-option v-for="v in filteredVideos" :key="v.id"
                       :label="`${v.is_mock ? '[MOCK] ' : ''}${v.prompt.slice(0, 40)} (${v.duration}s)`"
                       :value="v.id" :disabled="v.is_mock" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="publishForm.platform" placeholder="选择平台" style="width: 100%">
            <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value"
                       :disabled="!SUPPORTED_PLATFORMS.includes(p.value)" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台账号">
          <el-select v-model="publishForm.account_id" placeholder="选择账号" style="width: 100%">
            <el-option v-for="a in accountsForPlatform" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-alert v-if="sauInfo && !sauInfo.sau_installed" type="error" :closable="false" show-icon
                   title="未检测到 sau CLI" :description="`请先在 VM 上跑: ${sauInfo.login_command || 'pipx install social-auto-upload'}`" />
      </el-form>
      <template #footer>
        <el-button @click="showPublishDialog = false">取消</el-button>
        <el-button type="primary" :loading="publishing" :disabled="!canPublish" @click="onPublishNow">立即发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { platformApi, type PublishRecord, type PlatformAccount, type SauStatus } from '@/api/platforms'
import { contentApi, type Content } from '@/api/content'
import { aiApi, type VideoRecord } from '@/api/ai'
import { schedulerApi } from '@/api/scheduler'
import { PUBLISH_STATUSES, PLATFORM_OPTIONS, getStatusMeta, getPlatformName, formatDate } from '@/constants'

const route = useRoute()
const list = ref<PublishRecord[]>([])
const loading = ref(false)
const running = ref(false)
const filterStatus = ref('')
const filterPlatform = ref('')
const total = computed(() => list.value.length)

const filteredList = computed(() => {
  let res = list.value
  if (filterStatus.value) res = res.filter(r => r.status === filterStatus.value)
  if (filterPlatform.value) res = res.filter(r => r.platform === filterPlatform.value)
  return res
})

const statusClass = (s: string) => {
  if (s === 'success' || s === 'published') return 'ds-status--success'
  if (s === 'pending' || s === 'scheduled' || s === 'publishing' || s === 'freepublish_submitted') return 'ds-status--warning'
  if (s === 'failed') return 'ds-status--error'
  if (s === 'draft_added') return 'ds-status--neutral'
  return 'ds-status--neutral'
}

const statusLabel = (s: string): string => {
  // 中文状态标签
  const map: Record<string, string> = {
    pending: '待执行',
    scheduled: '已调度',
    uploading: '上传中',
    publishing: '发布中',
    draft_added: '草稿已写入',
    freepublish_submitted: '审核中',
    published: '已发布',
    failed: '失败',
  }
  return map[s] || s
}

const loadList = async () => {
  loading.value = true
  try { list.value = await platformApi.listPublishRecords() }
  catch (e: any) { ElMessage.error('加载失败: ' + (e.normalizedMessage || e.message)) }
  finally { loading.value = false }
}

const onRunDue = async () => {
  running.value = true
  try {
    const res = await schedulerApi.runDue()
    ElMessage.success(`已执行 ${res.executed} 个到期任务`)
    loadList()
  } catch (e: any) { ElMessage.error('执行失败: ' + (e.normalizedMessage || e.message)) }
  finally { running.value = false }
}

// ============ Phase 2: 立即发布弹窗 ============

const showPublishDialog = ref(false)
const publishing = ref(false)
const contents = ref<Content[]>([])
const allVideos = ref<VideoRecord[]>([])
const accounts = ref<PlatformAccount[]>([])
const sauInfo = ref<SauStatus | null>(null)
// MVP 阶段只有 douyin 接通了 adapter
const SUPPORTED_PLATFORMS = ref<string[]>([])

const publishForm = reactive({
  content_id: '',
  video_id: '',
  platform: 'douyin',
  account_id: '',
})

const filteredVideos = computed(() => {
  // 如果选了内容,只显示该内容关联的视频;否则显示所有非 mock
  if (publishForm.content_id) {
    return allVideos.value.filter(v => {
      const c = contents.value.find(c => c.id === publishForm.content_id)
      return c?.video_id === v.id
    })
  }
  return allVideos.value
})

const accountsForPlatform = computed(() =>
  accounts.value.filter(a => a.platform === publishForm.platform)
)

const canPublish = computed(() => Boolean(
  publishForm.content_id && publishForm.video_id && publishForm.platform && publishForm.account_id
))

const onContentChange = () => {
  // 选了内容后,自动尝试选该内容关联的视频
  const c = contents.value.find(c => c.id === publishForm.content_id)
  if (c?.video_id) publishForm.video_id = c.video_id
}

const openPublishDialog = async () => {
  showPublishDialog.value = true
  // 首次打开时一次性加载所有依赖
  if (contents.value.length === 0) {
    try {
      const [cs, vs, accs, sau] = await Promise.all([
        contentApi.list({ limit: 200 } as any),
        aiApi.videoList(50),
        platformApi.listAccounts(),
        platformApi.sauStatus(),
      ])
      contents.value = (cs as any).items || []
      allVideos.value = vs.items || []
      accounts.value = accs
      sauInfo.value = sau
      SUPPORTED_PLATFORMS.value = sau.supported_platforms
    } catch (e: any) {
      ElMessage.error('加载弹窗数据失败: ' + (e.normalizedMessage || e.message))
    }
  }
}

const onPublishNow = async () => {
  if (!canPublish.value) return
  publishing.value = true
  try {
    const result = await platformApi.publishVideo({
      content_id: publishForm.content_id,
      platform: publishForm.platform,
      account_id: publishForm.account_id,
      video_id: publishForm.video_id,
    })
    if (result.status === 'published') {
      ElMessage.success(`已发布: ${result.url || result.platform_publish_id || 'OK'}`)
    } else if (result.status === 'failed') {
      ElMessage.error(`发布失败: ${result.error || '未知错误'}`)
    } else {
      ElMessage.warning(`状态: ${result.status} — ${result.error || ''}`)
    }
    showPublishDialog.value = false
    loadList()
  } catch (e: any) {
    ElMessage.error('发布请求失败: ' + (e.normalizedMessage || e.message))
  } finally {
    publishing.value = false
  }
}

onMounted(async () => {
  await loadList()
  // 如果从 AI 视频页跳过来带 ?video_id=,预选
  const presetVideoId = route.query.video_id as string | undefined
  if (presetVideoId) {
    publishForm.video_id = presetVideoId
    await openPublishDialog()
  }
})
</script>

<style scoped>
.ds-table { background: var(--claude-ivory); border-radius: var(--radius-xl); overflow: hidden; }
.ds-table :deep(.ds-pill a) { color: inherit; }
</style>
