<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/ai">AI 工具</router-link>
        <span>·</span>
        <span>智能生成</span>
      </div>
      <h1 class="page-title">AI 智能生成</h1>
      <p class="page-subtitle">用 MiniMax 系列模型处理内容创作：摘要、播客、文案、视频脚本、图像，一站式。</p>
    </header>

    <el-tabs v-model="activeTab" class="ai-tabs ds-tabs">
      <!-- 内容摘要 -->
      <el-tab-pane name="summary">
        <template #label>
          <span class="tab-label">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h10M3 6h10M3 9h7M3 12h4" stroke-linecap="round" /></svg>
            <span>内容摘要</span>
          </span>
        </template>
        <section class="ds-card ai-tab-card">
          <h2 class="ds-card__title">把长文变摘要</h2>
          <p class="ds-card__lede">粘贴文章、链接内容、PDF 文本，自动提取关键要点。</p>
          <el-form :model="forms.summary" label-position="top">
            <el-form-item label="输入内容">
              <el-input v-model="forms.summary.content" type="textarea" :rows="8"
                       placeholder="粘贴文章或长文本..." maxlength="20000" show-word-limit />
            </el-form-item>
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.summary" :disabled="!forms.summary.content" @click="genSummary">
                {{ loading.summary ? '生成中…' : '生成摘要' }}
              </el-button>
            </el-form-item>
            <div v-if="results.summary" class="result-block">
              <div class="result-text">{{ results.summary.summary }}</div>
              <div class="result-meta">原文长度: {{ results.summary.original_length }} 字符</div>
            </div>
          </el-form>
        </section>
      </el-tab-pane>

      <!-- 播客脚本 -->
      <el-tab-pane name="podcast">
        <template #label>
          <span class="tab-label">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="2" width="6" height="9" rx="3" /><path d="M3 8a5 5 0 0010 0M8 13v2" stroke-linecap="round" /></svg>
            <span>播客脚本</span>
          </span>
        </template>
        <section class="ds-card ai-tab-card">
          <h2 class="ds-card__title">双人对话脚本</h2>
          <p class="ds-card__lede">把内容转成主播 A / 主播 B 的对话脚本，可直接朗读。</p>
          <el-form :model="forms.podcast" label-position="top">
            <el-form-item label="输入内容">
              <el-input v-model="forms.podcast.content" type="textarea" :rows="8"
                       placeholder="粘贴要转换为播客的内容..." maxlength="20000" show-word-limit />
            </el-form-item>
            <el-form-item label="风格">
              <el-radio-group v-model="forms.podcast.style">
                <el-radio-button value="casual">轻松闲聊</el-radio-button>
                <el-radio-button value="formal">正式访谈</el-radio-button>
                <el-radio-button value="educational">知识科普</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.podcast" :disabled="!forms.podcast.content" @click="genPodcast">
                {{ loading.podcast ? '生成中…' : '生成脚本' }}
              </el-button>
            </el-form-item>
            <div v-if="results.podcast" class="result-block">
              <div class="result-text">{{ results.podcast.script }}</div>
              <div class="result-meta">角色: {{ (results.podcast.characters || []).join(' / ') }} · 预计时长: {{ results.podcast.estimated_duration }}</div>
            </div>
          </el-form>
        </section>
      </el-tab-pane>

      <!-- 多平台文案 -->
      <el-tab-pane name="copy">
        <template #label>
          <span class="tab-label">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 5h12v8H2z M5 8h6" stroke-linecap="round" /></svg>
            <span>多平台文案</span>
          </span>
        </template>
        <section class="ds-card ai-tab-card">
          <h2 class="ds-card__title">平台定制文案</h2>
          <p class="ds-card__lede">给同一个主题生成不同平台的发布文案。抖音短、小红书温暖、公众号深度。</p>
          <el-form :model="forms.copy" label-position="top">
            <el-form-item label="主题">
              <el-input v-model="forms.copy.topic" placeholder="例如：AI 改变生活" />
            </el-form-item>
            <el-form-item label="目标平台">
              <el-select v-model="forms.copy.platform" style="width: 100%">
                <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.copy" :disabled="!forms.copy.topic" @click="genCopy">
                {{ loading.copy ? '生成中…' : '生成文案' }}
              </el-button>
            </el-form-item>
            <div v-if="results.copy" class="result-block">
              <div class="result-text">{{ results.copy.copy }}</div>
              <div class="result-meta">目标平台: {{ getPlatformName(results.copy.platform) }}</div>
            </div>
          </el-form>
        </section>
      </el-tab-pane>

      <!-- 视频脚本 -->
      <el-tab-pane name="video-script">
        <template #label>
          <span class="tab-label">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 4l9 4-9 4z" stroke-linejoin="round" /></svg>
            <span>视频脚本</span>
          </span>
        </template>
        <section class="ds-card ai-tab-card">
          <h2 class="ds-card__title">分镜脚本</h2>
          <p class="ds-card__lede">生成含画面、字幕、配乐建议的视频脚本。</p>
          <el-form :model="forms.videoScript" label-position="top">
            <el-form-item label="主题">
              <el-input v-model="forms.videoScript.topic" placeholder="例如：3 分钟了解 Vibe Coding" />
            </el-form-item>
            <el-form-item label="时长(秒)">
              <el-input-number v-model="forms.videoScript.duration" :min="15" :max="600" :step="15" />
            </el-form-item>
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.videoScript" :disabled="!forms.videoScript.topic" @click="genVideoScript">
                {{ loading.videoScript ? '生成中…' : '生成脚本' }}
              </el-button>
            </el-form-item>
            <div v-if="results.videoScript" class="result-block">
              <div class="result-text">{{ results.videoScript.script }}</div>
              <div class="result-meta">时长: {{ results.videoScript.duration }} 秒</div>
            </div>
          </el-form>
        </section>
      </el-tab-pane>

      <!-- 图像生成 (Apple shell + Claude body design) -->
      <el-tab-pane name="image">
        <template #label>
          <span class="tab-label">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="10" height="10" rx="1.5" /><circle cx="6" cy="6" r="1" /><path d="M3 11l3-3 3 3 2-2 2 2" stroke-linejoin="round" /></svg>
            <span>图像生成</span>
          </span>
        </template>
        <div class="image-gen-wrap">
          <div class="image-gen-card">
            <h3 class="card-title">把文字变成图片</h3>
            <p class="card-lede">image-01 驱动 · 越具体效果越好</p>

            <el-form :model="forms.image" label-position="top" class="image-form">
              <el-form-item label="提示词">
                <el-input v-model="forms.image.prompt" type="textarea" :rows="3"
                         placeholder="例如：一只橘猫坐在窗台看雨，傍晚城市天际线，35mm 胶片感" />
              </el-form-item>

              <div class="image-form-row">
                <el-form-item label="风格">
                  <el-radio-group v-model="forms.image.style" size="small">
                    <el-radio-button value="写实摄影">写实</el-radio-button>
                    <el-radio-button value="插画">插画</el-radio-button>
                    <el-radio-button value="3D 渲染">3D</el-radio-button>
                    <el-radio-button value="水墨">水墨</el-radio-button>
                    <el-radio-button value="极简矢量">矢量</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </div>

              <div class="image-form-row two-col">
                <el-form-item label="画幅">
                  <el-select v-model="forms.image.ratio">
                    <el-option label="1:1 主图" value="1:1" />
                    <el-option label="16:9 横版" value="16:9" />
                    <el-option label="9:16 竖版" value="9:16" />
                    <el-option label="4:3" value="4:3" />
                    <el-option label="3:4" value="3:4" />
                  </el-select>
                </el-form-item>
                <el-form-item label="数量">
                  <el-select v-model="forms.image.n">
                    <el-option :value="1" label="1 张" />
                    <el-option :value="2" label="2 张" />
                    <el-option :value="4" label="4 张" />
                  </el-select>
                </el-form-item>
              </div>

              <el-form-item>
                <el-button class="gen-btn" :loading="loading.image" :disabled="!forms.image.prompt" @click="genImage">
                  {{ loading.image ? '生成中…' : '生成图片' }}
                </el-button>
                <span class="cost-hint">预计 8-15 秒 · 当前真实模型</span>
              </el-form-item>
            </el-form>

            <div v-if="imageHistory.length === 0 && !loading.image" class="ds-empty">
              <div class="glyph">
                <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="6" y="6" width="20" height="20" rx="3" />
                  <circle cx="12" cy="12" r="2" />
                  <path d="M6 19l5-5 4 4 3-3 8 8" stroke-linejoin="round" />
                </svg>
              </div>
              <h4>还没有生成记录</h4>
              <p>输入提示词试试看。已配置真实 API，图片会真实生成。</p>
            </div>
          </div>

          <div v-if="imageHistory.length > 0" class="history-section">
            <div class="history-head">
              <h3>最近生成</h3>
              <span class="meta">共 {{ imageHistory.length }} 张 · {{ lastMockCount > 0 ? `${lastMockCount} 张为 mock` : '全部为真实生成' }}</span>
            </div>
            <div class="image-grid">
              <article v-for="img in imageHistory" :key="img.id" class="image-tile">
                <div class="thumb">
                  <img :src="img.image_url" :alt="img.prompt" loading="lazy" @error="onImgError" />
                  <span v-if="img.is_mock" class="mock-badge" title="mock 占位图">MOCK</span>
                  <span v-else class="real-badge" title="真实生成">REAL</span>
                </div>
                <div class="tile-meta">
                  <p class="prompt" :title="img.prompt">{{ img.prompt }}</p>
                  <div class="row">
                    <span>{{ img.ratio }} · {{ img.style }}</span>
                    <span class="ts">{{ formatTime(img.created_at) }}</span>
                  </div>
                </div>
              </article>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 视频生成 -->
      <el-tab-pane name="video">
        <template #label>
          <span class="tab-label">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="10" height="8" rx="1.5" /><path d="M6 6l4 2-4 2z" /></svg>
            <span>视频生成</span>
          </span>
        </template>
        <section class="ds-card ai-tab-card">
          <h2 class="ds-card__title">文字转视频</h2>
          <p class="ds-card__lede">MiniMax-Hailuo-03 模型（每日 3 次额度，3/6/10s 可选）。</p>
          <el-form :model="forms.video" label-position="top">
            <el-form-item label="视频描述">
              <el-input v-model="forms.video.prompt" type="textarea" :rows="3"
                       placeholder="例如：航拍镜头飞越山谷日落" />
            </el-form-item>
            <el-form-item label="时长与比例">
              <div class="row-pair">
                <el-select v-model="forms.video.duration" style="width: 110px">
                  <el-option v-for="d in DURATION_OPTIONS" :key="d" :label="`${d} 秒`" :value="d" />
                </el-select>
                <el-select v-model="forms.video.ratio" style="width: 130px">
                  <el-option v-for="r in RATIO_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
                </el-select>
                <el-input v-model="forms.video.style" placeholder="风格(可选,如 写实摄影)" style="flex: 1" />
              </div>
            </el-form-item>
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.video" :disabled="!forms.video.prompt" @click="genVideo">
                {{ loading.video ? '生成并下载中…' : '生成视频' }}
              </el-button>
            </el-form-item>
            <el-alert v-if="videoResult?.is_mock" type="warning" :closable="false" show-icon
                       :title="`Mock 模式:${videoResult.error || 'API key 未配置,使用占位文件'}`" />
            <div v-if="videoResult" class="result-block">
              <div class="result-meta">
                <span class="ds-pill" :class="`ds-pill--${videoResult.is_mock ? 'neutral' : 'success'}`">
                  {{ videoResult.is_mock ? 'MOCK' : 'REAL' }}
                </span>
                <span class="ds-pill" :class="`ds-pill--${videoResult.record.status === 'ready' ? 'success' : 'warning'}`">
                  {{ videoResult.record.status }}
                </span>
                <span class="caption mono">{{ videoResult.record.id }}</span>
              </div>
              <video v-if="!videoResult.is_mock && videoResult.record.video_url"
                     :src="videoResult.record.video_url" controls class="generated-video" />
              <p v-else class="caption">占位文件: {{ videoResult.record.local_path || '无' }}</p>
              <div class="result-actions">
                <el-button size="small" :disabled="!videoResult.is_mock" @click="goPublishRecords(videoResult.record.id)">
                  去发布
                </el-button>
                <el-button size="small" plain @click="videoResult = null">清除</el-button>
              </div>
            </div>
          </el-form>

          <!-- 视频历史 -->
          <div class="video-history" v-if="videoHistory.length > 0">
            <h3 class="ds-section-head">历史视频 ({{ videoHistory.length }})</h3>
            <div class="video-grid">
              <article v-for="v in videoHistory" :key="v.id" class="video-card">
                <div class="video-card-head">
                  <span class="ds-pill" :class="`ds-pill--${v.is_mock ? 'neutral' : 'success'}`">
                    {{ v.is_mock ? 'MOCK' : 'REAL' }}
                  </span>
                  <span class="ds-pill" :class="`ds-pill--${v.status === 'ready' ? 'success' : 'warning'}`">
                    {{ v.status }}
                  </span>
                </div>
                <div class="video-card-body">
                  <p class="video-prompt">{{ v.prompt.slice(0, 60) }}{{ v.prompt.length > 60 ? '…' : '' }}</p>
                  <p class="caption">{{ v.duration }}s · {{ v.ratio }} · {{ formatTime(v.created_at) }}</p>
                </div>
                <div class="video-card-actions">
                  <el-button size="small" :disabled="v.is_mock" @click="goPublishRecords(v.id)">发布</el-button>
                  <el-button size="small" plain @click="deleteVideo(v.id)">删除</el-button>
                </div>
              </article>
            </div>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { aiApi, type VideoRecord, type VideoGenerateResponse } from '@/api/ai'
import { settingsApi } from '@/api/settings'
import { PLATFORM_OPTIONS, getPlatformName } from '@/constants'

const router = useRouter()
const activeTab = ref('summary')
const loading = reactive({ summary: false, podcast: false, copy: false, videoScript: false, image: false, video: false })
const forms = reactive({
  summary: { content: '' },
  podcast: { content: '', style: 'casual' },
  copy: { topic: '', platform: 'douyin' },
  videoScript: { topic: '', duration: 60 },
  image: { prompt: '', style: '写实摄影', ratio: '1:1', n: 1 },
  video: { prompt: '', duration: 6, ratio: '16:9', style: '' },
})
const results = reactive<any>({})
const imageHistory = ref<any[]>([])
const videoHistory = ref<VideoRecord[]>([])
const videoResult = ref<VideoGenerateResponse | null>(null)
const lastMockCount = ref(0)

// 视频表单的常量
const DURATION_OPTIONS = [3, 6, 10]
const RATIO_OPTIONS = [
  { value: '16:9', label: '16:9 横屏 (MiniMax 原生)' },
  { value: '9:16', label: '9:16 竖屏 (抖音推荐)' },
  { value: '1:1', label: '1:1 方形' },
]

const formatTime = (iso: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  return d.toLocaleDateString('zh-CN')
}

const checkConfigured = async () => {
  try {
    const s = await settingsApi.get()
    if (!s.configured) ElMessage.warning('请先在设置中配置 API Key')
  } catch (e) {}
}

const onImgError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}

const handleError = (e: any, op: string) => {
  const msg = e.normalizedMessage || e.message || '生成失败'
  if (msg.includes('API Key') || msg.includes('api_key') || msg.includes('未配置')) {
    ElMessage.error(`AI 服务未配置：请先在设置页面配置 API Key`)
  } else {
    ElMessage.error(`${op} 失败: ${msg}`)
  }
}

const genSummary = async () => {
  loading.summary = true
  try { results.summary = await aiApi.summary(forms.summary.content) }
  catch (e: any) { handleError(e, '摘要生成') }
  finally { loading.summary = false }
}

const genPodcast = async () => {
  loading.podcast = true
  try { results.podcast = await aiApi.podcastScript(forms.podcast.content, forms.podcast.style) }
  catch (e: any) { handleError(e, '播客脚本生成') }
  finally { loading.podcast = false }
}

const genCopy = async () => {
  loading.copy = true
  try { results.copy = await aiApi.copy(forms.copy.topic, forms.copy.platform) }
  catch (e: any) { handleError(e, '文案生成') }
  finally { loading.copy = false }
}

const genVideoScript = async () => {
  loading.videoScript = true
  try { results.videoScript = await aiApi.videoScript(forms.videoScript.topic, forms.videoScript.duration) }
  catch (e: any) { handleError(e, '视频脚本生成') }
  finally { loading.videoScript = false }
}

const genImage = async () => {
  loading.image = true
  try {
    const resp = await aiApi.image({
      prompt: forms.image.prompt, style: forms.image.style,
      ratio: forms.image.ratio, n: forms.image.n,
    })
    results.image = resp
    lastMockCount.value = resp.is_mock ? resp.count : 0
    try {
      const list = await aiApi.imageList(50)
      imageHistory.value = list.items || []
    } catch (_) {}
    if (resp.is_mock) ElMessage.warning(`已用 mock 模式生成 ${resp.count} 张：${resp.error || 'API key 未配置'}`)
    else ElMessage.success(`已生成 ${resp.count} 张图片`)
  } catch (e: any) { handleError(e, '图像生成') }
  finally { loading.image = false }
}

const genVideo = async () => {
  loading.video = true
  try {
    const resp = await aiApi.videoGenerate({
      prompt: forms.video.prompt,
      duration: forms.video.duration,
      ratio: forms.video.ratio,
      style: forms.video.style || undefined,
    })
    videoResult.value = resp
    if (resp.is_mock) {
      ElMessage.warning(`已用 mock 模式:${resp.error || 'API key 未配置'}`)
    } else {
      ElMessage.success(`已生成视频 (${resp.record.duration}s)`)
    }
    await loadVideoHistory()
  } catch (e: unknown) {
    handleError(e, '视频生成')
  } finally {
    loading.video = false
  }
}

const loadVideoHistory = async () => {
  try {
    const list = await aiApi.videoList(50)
    videoHistory.value = list.items || []
  } catch (_) { /* silent */ }
}

const deleteVideo = async (id: string) => {
  try {
    await ElMessageBox.confirm('删除该视频记录?(磁盘占位文件也会被清理)', '确认', { type: 'warning' })
  } catch { return }
  try {
    await aiApi.videoDelete(id)
    videoHistory.value = videoHistory.value.filter(v => v.id !== id)
    ElMessage.success('已删除')
  } catch (e: unknown) {
    handleError(e, '删除视频')
  }
}

const goPublishRecords = (videoId: string) => {
  router.push({ path: '/publish-records', query: { video_id: videoId } })
}

// 切到 video tab 时拉历史(避免每次 mount 都打)
watch(activeTab, (tab) => {
  if (tab === 'video') loadVideoHistory()
})

onMounted(async () => {
  checkConfigured()
  try {
    const list = await aiApi.imageList(50)
    imageHistory.value = list.items || []
  } catch (_) {}
})
</script>

<style scoped>
.ds-tabs { margin-top: 24px; }
.tab-label {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 14px;
}
.tab-label svg { color: var(--claude-terracotta); }

.primary-cta {
  background: var(--claude-terracotta) !important;
  border: 0 !important; color: var(--claude-ivory) !important;
  border-radius: 12px !important;
  height: 40px !important; padding: 0 22px !important;
  font-weight: 500 !important;
}
.primary-cta:hover { background: var(--claude-coral) !important; }

.generated-video { max-width: 100%; border-radius: var(--radius-lg); margin-top: 12px; }

.row-pair { display: flex; gap: 8px; align-items: center; }
.video-history { margin-top: 32px; border-top: 1px solid var(--claude-border-cream); padding-top: 24px; }
.video-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px; margin-top: 12px;
}
.video-card {
  border: 1px solid var(--claude-border-cream);
  background: var(--claude-parchment);
  border-radius: var(--radius-lg);
  padding: 14px; display: flex; flex-direction: column; gap: 8px;
}
.video-card-head, .video-card-actions { display: flex; gap: 6px; align-items: center; }
.video-card-body { flex: 1; }
.video-prompt { font-size: 13px; line-height: 1.4; color: var(--claude-text-primary); margin: 0 0 6px; }
.result-meta { display: flex; gap: 6px; align-items: center; margin-bottom: 8px; }
.result-actions { display: flex; gap: 8px; margin-top: 8px; }

@media (max-width: 640px) { }
.gen-btn {
  background: var(--claude-terracotta) !important; border: 0 !important; color: var(--claude-ivory) !important;
  border-radius: 12px !important; padding: 10px 24px !important;
  font-weight: 500 !important; font-size: 15px !important;
}
.gen-btn:hover { background: var(--claude-coral) !important; }
.cost-hint { margin-left: 14px; font-size: 12px; color: var(--claude-stone); }

</style>
