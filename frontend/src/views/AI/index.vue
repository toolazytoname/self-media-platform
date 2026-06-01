<template>
  <div class="ai-page">
    <el-row :gutter="24">
      <!-- 左侧：功能选择 -->
      <el-col :span="6">
        <el-card class="feature-card">
          <template #header>
            <div class="card-title">
              <span>🤖</span>
              <span>AI 功能</span>
            </div>
          </template>

          <div class="feature-list">
            <div
              v-for="feature in features"
              :key="feature.key"
              :class="['feature-item', { active: selectedFeature === feature.key }]"
              @click="selectedFeature = feature.key"
            >
              <span class="feature-icon">{{ feature.icon }}</span>
              <span class="feature-name">{{ feature.name }}</span>
            </div>
          </div>
        </el-card>

        <el-card class="tips-card">
          <template #header>
            <div class="card-title">
              <span>💡</span>
              <span>使用提示</span>
            </div>
          </template>
          <div class="tips-content">
            <p v-if="!apiConfigured" class="warning-text">
              ⚠️ 请先在后台配置 MiniMax API Key
            </p>
            <p v-else class="tip-text">
              基于 MiniMax M3 大模型，支持文本、图像、语音、音乐生成
            </p>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：生成面板 -->
      <el-col :span="18">
        <el-card class="generate-card">
          <template #header>
            <div class="card-title">
              <span>{{ currentFeatureName }}</span>
            </div>
          </template>

          <!-- 内容摘要 -->
          <el-form v-if="selectedFeature === 'summary'" label-position="top">
            <el-form-item label="输入内容">
              <el-input v-model="inputContent" type="textarea" :rows="8" placeholder="输入要摘要的内容，支持长文本、URL或粘贴文章..." />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="generateSummary" :loading="loading">
                生成摘要
              </el-button>
            </el-form-item>
            <el-form-item v-if="result" label="生成结果">
              <div class="result-box">{{ result }}</div>
            </el-form-item>
          </el-form>

          <!-- 播客脚本 -->
          <el-form v-else-if="selectedFeature === 'podcast'" label-position="top">
            <el-form-item label="输入内容">
              <el-input v-model="inputContent" type="textarea" :rows="8" placeholder="输入内容，AI将生成双人对话播客脚本..." />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="generatePodcast" :loading="loading">
                生成播客脚本
              </el-button>
            </el-form-item>
            <el-form-item v-if="result" label="生成的脚本">
              <div class="result-box script-result">{{ result }}</div>
            </el-form-item>
          </el-form>

          <!-- 文案生成 -->
          <el-form v-else-if="selectedFeature === 'copy'" label-position="top">
            <el-form-item label="主题">
              <el-input v-model="topic" placeholder="输入要生成文案的主题..." />
            </el-form-item>
            <el-form-item label="目标平台">
              <el-select v-model="targetPlatform" style="width: 100%">
                <el-option label="抖音" value="douyin" />
                <el-option label="小红书" value="xiaohongshu" />
                <el-option label="头条" value="toutiao" />
                <el-option label="公众号" value="wechat" />
                <el-option label="YouTube" value="youtube" />
                <el-option label="B站" value="bilibili" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="generateCopy" :loading="loading">
                生成文案
              </el-button>
            </el-form-item>
            <el-form-item v-if="result" label="生成的文案">
              <div class="result-box">{{ result }}</div>
            </el-form-item>
          </el-form>

          <!-- 图片生成 -->
          <el-form v-else-if="selectedFeature === 'image'" label-position="top">
            <el-form-item label="图片描述">
              <el-input v-model="imagePrompt" type="textarea" :rows="4" placeholder="描述你想要生成的图片..." />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="generateImage" :loading="loading">
                生成图片
              </el-button>
            </el-form-item>
            <el-form-item v-if="imageUrl" label="生成结果">
              <div class="image-result">
                <img :src="imageUrl" alt="Generated" />
              </div>
            </el-form-item>
          </el-form>

          <!-- 视频脚本 -->
          <el-form v-else-if="selectedFeature === 'script'" label-position="top">
            <el-form-item label="视频主题">
              <el-input v-model="videoTopic" placeholder="输入视频主题..." />
            </el-form-item>
            <el-form-item label="时长(秒)">
              <el-input-number v-model="videoDuration" :min="15" :max="180" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="generateScript" :loading="loading">
                生成脚本
              </el-button>
            </el-form-item>
            <el-form-item v-if="result" label="生成的脚本">
              <div class="result-box script-result">{{ result }}</div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const features = [
  { key: 'summary', name: '内容摘要', icon: '📄' },
  { key: 'podcast', name: '播客脚本', icon: '🎙️' },
  { key: 'copy', name: '文案生成', icon: '✍️' },
  { key: 'image', name: '图片生成', icon: '🖼️' },
  { key: 'script', name: '视频脚本', icon: '🎬' }
]

const selectedFeature = ref('summary')
const inputContent = ref('')
const topic = ref('')
const imagePrompt = ref('')
const videoTopic = ref('')
const videoDuration = ref(60)
const targetPlatform = ref('douyin')
const result = ref('')
const imageUrl = ref('')
const loading = ref(false)
const apiConfigured = ref(false) // 需要后端配置后检查

const currentFeatureName = computed(() => {
  return features.find(f => f.key === selectedFeature.value)?.name || ''
})

const handleError = (error: any) => {
  if (error.response?.status === 401 || error.message?.includes('401')) {
    result.value = '⚠️ 请在服务器配置 MiniMax API Key\n\n步骤：\n1. 创建 backend/.env 文件\n2. 添加 MINIMAX_API_KEY=你的API密钥\n3. 重启后端服务'
    apiConfigured.value = false
  } else if (error.response?.status === 500) {
    result.value = '⚠️ AI 服务暂时不可用，请检查 API 配置或网络连接'
  } else {
    result.value = '⚠️ 发生未知错误: ' + (error.message || 'Unknown error')
  }
}

const generateSummary = async () => {
  if (!inputContent.value) {
    ElMessage.warning('请输入内容')
    return
  }
  loading.value = true
  result.value = ''
  try {
    const res = await axios.post('/api/ai/summary', { content: inputContent.value })
    result.value = res.data.summary || '生成完成'
    apiConfigured.value = true
  } catch (error: any) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

const generatePodcast = async () => {
  if (!inputContent.value) {
    ElMessage.warning('请输入内容')
    return
  }
  loading.value = true
  result.value = ''
  try {
    const res = await axios.post('/api/ai/podcast/script', { content: inputContent.value })
    result.value = res.data.script || '生成完成'
    apiConfigured.value = true
  } catch (error: any) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

const generateCopy = async () => {
  if (!topic.value) {
    ElMessage.warning('请输入主题')
    return
  }
  loading.value = true
  result.value = ''
  try {
    const res = await axios.post('/api/ai/copy', {
      topic: topic.value,
      platform: targetPlatform.value
    })
    result.value = res.data.copy || '生成完成'
    apiConfigured.value = true
  } catch (error: any) {
    handleError(error)
  } finally {
    loading.value = false
  }
}

const generateImage = async () => {
  if (!imagePrompt.value) {
    ElMessage.warning('请输入图片描述')
    return
  }
  loading.value = true
  imageUrl.value = ''
  try {
    const res = await axios.post('/api/ai/image', { prompt: imagePrompt.value })
    imageUrl.value = res.data.image_url || ''
    apiConfigured.value = true
  } catch (error: any) {
    ElMessage.error('生成失败: ' + (error.message || 'API 配置错误'))
    handleError(error)
  } finally {
    loading.value = false
  }
}

const generateScript = async () => {
  if (!videoTopic.value) {
    ElMessage.warning('请输入视频主题')
    return
  }
  loading.value = true
  result.value = ''
  try {
    const res = await axios.post('/api/ai/video/script', {
      topic: videoTopic.value,
      duration: videoDuration.value
    })
    result.value = res.data.script || '生成完成'
    apiConfigured.value = true
  } catch (error: any) {
    handleError(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ai-page {
  padding: 0;
}

.feature-card,
.generate-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.feature-card {
  height: auto;
}

.tips-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  margin-top: 16px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.03);
}

.feature-item:hover {
  background: rgba(0, 212, 255, 0.1);
}

.feature-item.active {
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.2) 0%, rgba(0, 212, 255, 0.05) 100%);
  border-right: 3px solid #00d4ff;
}

.feature-icon {
  font-size: 20px;
}

.feature-name {
  font-size: 14px;
  color: #e0e0e0;
}

.tips-content {
  font-size: 13px;
  color: #888;
  line-height: 1.6;
}

.warning-text {
  color: #ff9f43;
  padding: 12px;
  background: rgba(255, 159, 67, 0.1);
  border-radius: 8px;
}

.tip-text {
  color: #666;
}

.result-box {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  padding: 16px;
  min-height: 150px;
  color: #e0e0e0;
  line-height: 1.8;
  white-space: pre-wrap;
}

.script-result {
  min-height: 300px;
}

.image-result {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}

.image-result img {
  max-width: 100%;
  max-height: 400px;
  border-radius: 8px;
}
</style>