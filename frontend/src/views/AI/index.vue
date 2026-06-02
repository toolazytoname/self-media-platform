<template>
  <div class="ai-page">
    <el-card class="ai-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>🤖</span>
            <span>AI 智能生成</span>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="ai-tabs">
        <!-- 内容摘要 -->
        <el-tab-pane label="📝 内容摘要" name="summary">
          <el-form :model="forms.summary" label-position="top">
            <el-form-item label="输入内容">
              <el-input v-model="forms.summary.content" type="textarea" :rows="8"
                       placeholder="粘贴文章或长文本..." maxlength="20000" show-word-limit />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="genSummary" :loading="loading.summary" :disabled="!forms.summary.content">
                生成摘要
              </el-button>
            </el-form-item>
            <el-form-item v-if="results.summary" label="生成结果">
              <div class="result-box">
                <div class="result-text">{{ results.summary.summary }}</div>
                <div class="result-meta">原文长度: {{ results.summary.original_length }} 字符</div>
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 播客脚本 -->
        <el-tab-pane label="🎙️ 播客脚本" name="podcast">
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
              <el-button type="primary" @click="genPodcast" :loading="loading.podcast" :disabled="!forms.podcast.content">
                生成脚本
              </el-button>
            </el-form-item>
            <el-form-item v-if="results.podcast" label="生成结果">
              <div class="result-box">
                <div class="result-text">{{ results.podcast.script }}</div>
                <div class="result-meta">
                  角色: {{ (results.podcast.characters || []).join(' / ') }} |
                  预计时长: {{ results.podcast.estimated_duration }}
                </div>
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 多平台文案 -->
        <el-tab-pane label="📱 多平台文案" name="copy">
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
              <el-button type="primary" @click="genCopy" :loading="loading.copy" :disabled="!forms.copy.topic">
                生成文案
              </el-button>
            </el-form-item>
            <el-form-item v-if="results.copy" label="生成结果">
              <div class="result-box">
                <div class="result-text">{{ results.copy.copy }}</div>
                <div class="result-meta">目标平台: {{ getPlatformName(results.copy.platform) }}</div>
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 视频脚本 -->
        <el-tab-pane label="🎬 视频脚本" name="video-script">
          <el-form :model="forms.videoScript" label-position="top">
            <el-form-item label="主题">
              <el-input v-model="forms.videoScript.topic" placeholder="例如：3 分钟了解 Vibe Coding" />
            </el-form-item>
            <el-form-item label="时长(秒)">
              <el-input-number v-model="forms.videoScript.duration" :min="15" :max="600" :step="15" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="genVideoScript" :loading="loading.videoScript" :disabled="!forms.videoScript.topic">
                生成脚本
              </el-button>
            </el-form-item>
            <el-form-item v-if="results.videoScript" label="生成结果">
              <div class="result-box">
                <div class="result-text">{{ results.videoScript.script }}</div>
                <div class="result-meta">时长: {{ results.videoScript.duration }} 秒</div>
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 图像生成 -->
        <el-tab-pane label="🖼️ 图像生成" name="image">
          <el-form :model="forms.image" label-position="top">
            <el-form-item label="图像描述 (英文 prompt 效果更佳)">
              <el-input v-model="forms.image.prompt" type="textarea" :rows="3"
                       placeholder="例如：A cute cat sitting on a laptop keyboard, soft lighting, high quality" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="genImage" :loading="loading.image" :disabled="!forms.image.prompt">
                生成图像
              </el-button>
            </el-form-item>
            <el-form-item v-if="results.image" label="生成结果">
              <div class="result-box">
                <img v-if="results.image.image_url" :src="results.image.image_url" alt="AI generated" class="generated-image" @error="onImgError" />
                <div v-else class="result-text">⚠️ 图像生成服务未配置（请在设置中检查 API Key）</div>
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 视频生成 -->
        <el-tab-pane label="🎥 视频生成" name="video">
          <el-form :model="forms.video" label-position="top">
            <el-form-item label="视频描述 (英文 prompt 效果更佳)">
              <el-input v-model="forms.video.prompt" type="textarea" :rows="3"
                       placeholder="例如：A drone shot flying over a beautiful mountain valley at sunset" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="genVideo" :loading="loading.video" :disabled="!forms.video.prompt">
                生成视频
              </el-button>
            </el-form-item>
            <el-form-item v-if="results.video" label="任务状态">
              <div class="result-box">
                <p>任务 ID: <code>{{ results.video.job_id }}</code></p>
                <p>状态: <el-tag>{{ results.video.status }}</el-tag></p>
                <el-button size="small" @click="checkVideoStatus" :disabled="!results.video.job_id">
                  刷新状态
                </el-button>
                <video v-if="results.video.video_url" :src="results.video.video_url" controls class="generated-video"></video>
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api/ai'
import { settingsApi } from '@/api/settings'
import { PLATFORM_OPTIONS, getPlatformName } from '@/constants'

const activeTab = ref('summary')
const loading = reactive({
  summary: false,
  podcast: false,
  copy: false,
  videoScript: false,
  image: false,
  video: false,
})

const forms = reactive({
  summary: { content: '' },
  podcast: { content: '', style: 'casual' },
  copy: { topic: '', platform: 'douyin' },
  videoScript: { topic: '', duration: 60 },
  image: { prompt: '' },
  video: { prompt: '' },
})

const results = reactive<any>({})

const checkConfigured = async () => {
  try {
    const s = await settingsApi.get()
    if (!s.configured) {
      ElMessage.warning('请先在设置中配置 API Key')
    }
  } catch (e) {}
}

const onImgError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}

const handleError = (e: any, op: string) => {
  const msg = e.normalizedMessage || e.message || '生成失败'
  if (msg.includes('API Key') || msg.includes('api_key') || msg.includes('未配置')) {
    ElMessage.error(`❌ AI 服务未配置：请先在"设置"页面配置 API Key`)
  } else {
    ElMessage.error(`${op} 失败: ${msg}`)
  }
}

const genSummary = async () => {
  loading.summary = true
  try {
    results.summary = await aiApi.summary(forms.summary.content)
  } catch (e: any) { handleError(e, '摘要生成') }
  finally { loading.summary = false }
}

const genPodcast = async () => {
  loading.podcast = true
  try {
    results.podcast = await aiApi.podcastScript(forms.podcast.content, forms.podcast.style)
  } catch (e: any) { handleError(e, '播客脚本生成') }
  finally { loading.podcast = false }
}

const genCopy = async () => {
  loading.copy = true
  try {
    results.copy = await aiApi.copy(forms.copy.topic, forms.copy.platform)
  } catch (e: any) { handleError(e, '文案生成') }
  finally { loading.copy = false }
}

const genVideoScript = async () => {
  loading.videoScript = true
  try {
    results.videoScript = await aiApi.videoScript(forms.videoScript.topic, forms.videoScript.duration)
  } catch (e: any) { handleError(e, '视频脚本生成') }
  finally { loading.videoScript = false }
}

const genImage = async () => {
  loading.image = true
  try {
    results.image = await aiApi.image(forms.image.prompt)
  } catch (e: any) { handleError(e, '图像生成') }
  finally { loading.image = false }
}

const genVideo = async () => {
  loading.video = true
  try {
    results.video = await aiApi.videoGenerate(forms.video.prompt)
    if (results.video?.job_id) {
      // 启动轮询
      pollVideoStatus(results.video.job_id)
    }
  } catch (e: any) { handleError(e, '视频生成') }
  finally { loading.video = false }
}

const checkVideoStatus = async () => {
  if (!results.video?.job_id) return
  try {
    const status = await aiApi.videoStatus(results.video.job_id)
    results.video = { ...results.video, ...status }
    if (status.status === 'completed' || status.status === 'failed') {
      ElMessage.success(status.status === 'completed' ? '视频生成完成' : '视频生成失败')
    }
  } catch (e: any) { handleError(e, '查询视频状态') }
}

const pollVideoStatus = (jobId: string) => {
  let attempts = 0
  const maxAttempts = 30
  const timer = setInterval(async () => {
    attempts++
    try {
      const status = await aiApi.videoStatus(jobId)
      results.video = { ...results.video, ...status }
      if (status.status === 'completed' || status.status === 'failed' || attempts >= maxAttempts) {
        clearInterval(timer)
        if (status.status === 'completed') {
          ElMessage.success('视频生成完成')
        } else if (status.status === 'failed') {
          ElMessage.error('视频生成失败')
        } else if (attempts >= maxAttempts) {
          ElMessage.warning('视频生成超时，请手动刷新')
        }
      }
    } catch (e) {
      clearInterval(timer)
    }
  }, 5000)
}

onMounted(checkConfigured)
</script>

<style scoped>
.ai-page { padding: 0; }
.ai-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; color: #fff; }
.ai-tabs :deep(.el-tabs__nav-wrap)::after { background: rgba(255, 255, 255, 0.08); }
.ai-tabs :deep(.el-tabs__item) { color: #a0a0b0; }
.ai-tabs :deep(.el-tabs__item.is-active) { color: #00d4ff; }
.result-box {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  padding: 16px;
}
.result-text { font-size: 14px; line-height: 1.8; color: #e0e0e0; white-space: pre-wrap; }
.result-meta { font-size: 12px; color: #888; margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.05); }
.generated-image { max-width: 100%; border-radius: 8px; margin-top: 8px; }
.generated-video { max-width: 100%; border-radius: 8px; margin-top: 12px; }
code { background: rgba(0, 0, 0, 0.3); padding: 2px 6px; border-radius: 4px; font-family: monospace; }
</style>
