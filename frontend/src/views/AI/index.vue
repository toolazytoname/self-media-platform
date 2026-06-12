<template>
  <div>
    <header class="page-header">
      <div class="breadcrumb">
        <router-link to="/ai">AI 工具</router-link>
        <span>·</span>
        <span>智能生成</span>
      </div>
      <h1 class="page-title">AI 智能生成</h1>
      <p class="page-subtitle">用 MiniMax / Claude / OpenAI 处理内容创作:摘要、文案、脚本、扩写、标题、标签,以及图像与视频生成。</p>
    </header>

    <div class="ai-layout">
      <!-- 左侧 220px 创作侧边栏(Phase C.1 参考 AiToEarn) -->
      <aside class="ai-sidebar">
        <div v-for="grp in MODULE_GROUPS" :key="grp.id" class="sidebar-section">
          <h3 class="sidebar-section-title">{{ grp.label }}</h3>
          <button
            v-for="m in grp.modules"
            :key="m.id"
            class="sidebar-item"
            :class="{ active: activeTab === m.id }"
            @click="activeTab = m.id"
          >
            <span class="item-icon" v-html="m.icon"></span>
            <span class="item-label">{{ m.label }}</span>
            <span v-if="m.isNew" class="item-badge">新</span>
          </button>
        </div>

        <div class="sidebar-section">
          <router-link to="/settings" class="sidebar-link">设置 →</router-link>
        </div>
      </aside>

      <!-- 右侧主区:当前模块的 form + result -->
      <main class="ai-main">
        <!-- ====== 内容摘要 ====== -->
        <section v-if="activeTab === 'summary'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">把长文变摘要</h2>
          <p class="ds-card__lede">粘贴文章、链接内容、PDF 文本,自动提取关键要点。</p>
          <el-form :model="forms.summary" label-position="top">
            <el-form-item label="输入内容">
              <el-input v-model="forms.summary.content" type="textarea" :rows="8"
                       placeholder="粘贴文章或长文本..." maxlength="20000" show-word-limit />
            </el-form-item>
            <ProviderPicker v-model="forms.summary" />
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.summary" :disabled="!forms.summary.content" @click="genSummary">
                {{ loading.summary ? '生成中…' : '生成摘要' }}
              </el-button>
            </el-form-item>
            <ResultBlock v-if="results.summary" :text="results.summary.summary"
                         :meta="`原文长度: ${results.summary.original_length} 字符`"
                         @apply="onApplyTo('body', results.summary.summary)" />
          </el-form>
        </section>

        <!-- ====== 播客脚本 ====== -->
        <section v-else-if="activeTab === 'podcast'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">双人对话脚本</h2>
          <p class="ds-card__lede">把内容转成主播 A / 主播 B 的对话脚本,可以直接朗读。</p>
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
            <ProviderPicker v-model="forms.podcast" />
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.podcast" :disabled="!forms.podcast.content" @click="genPodcast">
                {{ loading.podcast ? '生成中…' : '生成脚本' }}
              </el-button>
            </el-form-item>
            <ResultBlock v-if="results.podcast" :text="results.podcast.script"
                         :meta="`角色: ${(results.podcast.characters || []).join(' / ')} · 预计时长: ${results.podcast.estimated_duration}`"
                         @apply="onApplyTo('body', results.podcast.script)" />
          </el-form>
        </section>

        <!-- ====== 多平台文案 ====== -->
        <section v-else-if="activeTab === 'copy'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">平台定制文案</h2>
          <p class="ds-card__lede">给同一个主题生成不同平台的发布文案。</p>
          <el-form :model="forms.copy" label-position="top">
            <el-form-item label="主题">
              <el-input v-model="forms.copy.topic" placeholder="例如:AI 改变生活" />
            </el-form-item>
            <el-form-item label="目标平台">
              <el-select v-model="forms.copy.platform" style="width: 100%">
                <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
              </el-select>
            </el-form-item>
            <ProviderPicker v-model="forms.copy" />
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.copy" :disabled="!forms.copy.topic" @click="genCopy">
                {{ loading.copy ? '生成中…' : '生成文案' }}
              </el-button>
            </el-form-item>
            <ResultBlock v-if="results.copy" :text="results.copy.copy"
                         :meta="`目标平台: ${getPlatformName(results.copy.platform)}`"
                         @apply="onApplyTo('body', results.copy.copy)" />
          </el-form>
        </section>

        <!-- ====== 视频脚本 ====== -->
        <section v-else-if="activeTab === 'video-script'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">视频脚本</h2>
          <p class="ds-card__lede">生成分镜 / 字幕 / 配音的视频脚本,带时长控制。</p>
          <el-form :model="forms.videoScript" label-position="top">
            <el-form-item label="主题">
              <el-input v-model="forms.videoScript.topic" placeholder="例如:3 分钟了解 Vibe Coding" />
            </el-form-item>
            <el-form-item label="目标时长(秒)">
              <el-input-number v-model="forms.videoScript.duration" :min="15" :max="600" :step="15" />
            </el-form-item>
            <ProviderPicker v-model="forms.videoScript" />
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.videoScript"
                         :disabled="!forms.videoScript.topic" @click="genVideoScript">
                {{ loading.videoScript ? '生成中…' : '生成脚本' }}
              </el-button>
            </el-form-item>
            <ResultBlock v-if="results.videoScript" :text="results.videoScript.script"
                         :meta="`时长: ${results.videoScript.duration} 秒`"
                         @apply="onApplyTo('body', results.videoScript.script)" />
          </el-form>
        </section>

        <!-- ====== Phase B.1: 扩写 ====== -->
        <section v-else-if="activeTab === 'expand'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">把短文拉长</h2>
          <p class="ds-card__lede">短内容 → 3 档长度(短/中/长),3 种语气(轻松/正式/学术)。</p>
          <el-form :model="forms.expand" label-position="top">
            <el-form-item label="原文">
              <el-input v-model="forms.expand.content" type="textarea" :rows="5"
                       placeholder="一段话或一两个想法..." maxlength="10000" show-word-limit />
            </el-form-item>
            <el-form-item label="目标长度与语气">
              <div class="row-pair">
                <el-select v-model="forms.expand.target_length" style="width: 130px">
                  <el-option label="短 (200-300 字)" value="short" />
                  <el-option label="中 (600-800 字)" value="medium" />
                  <el-option label="长 (1500-2000 字)" value="long" />
                </el-select>
                <el-select v-model="forms.expand.tone" style="width: 130px">
                  <el-option label="轻松" value="casual" />
                  <el-option label="正式" value="formal" />
                  <el-option label="学术" value="academic" />
                </el-select>
              </div>
            </el-form-item>
            <ProviderPicker v-model="forms.expand" />
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.expand"
                         :disabled="!forms.expand.content" @click="genExpand">
                {{ loading.expand ? '扩写中…' : '扩写' }}
              </el-button>
            </el-form-item>
            <ResultBlock v-if="results.expand" :text="results.expand.expanded"
                         :meta="`原始 ${results.expand.original_length} 字 → 扩写 ${results.expand.expanded_length} 字 (${results.expand.ratio}x)`"
                         @apply="onApplyTo('body', results.expand.expanded)" />
          </el-form>
        </section>

        <!-- ====== Phase B.2: 标题生成 ====== -->
        <section v-else-if="activeTab === 'titles'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">AI 拟标题</h2>
          <p class="ds-card__lede">基于内容生成 N 个候选标题,可指定平台和风格。</p>
          <el-form :model="forms.titles" label-position="top">
            <el-form-item label="原文">
              <el-input v-model="forms.titles.content" type="textarea" :rows="5"
                       placeholder="粘贴正文..." maxlength="10000" show-word-limit />
            </el-form-item>
            <el-form-item label="候选数 / 平台 / 风格">
              <div class="row-pair">
                <el-input-number v-model="forms.titles.n" :min="1" :max="10" style="width: 110px" />
                <el-select v-model="forms.titles.platform" placeholder="不限平台" clearable style="width: 140px">
                  <el-option v-for="p in PLATFORM_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
                </el-select>
                <el-select v-model="forms.titles.style" style="width: 130px">
                  <el-option label="抓眼球" value="clickbait" />
                  <el-option label="中性" value="neutral" />
                  <el-option label="专业" value="professional" />
                </el-select>
              </div>
            </el-form-item>
            <ProviderPicker v-model="forms.titles" />
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.titles"
                         :disabled="!forms.titles.content" @click="genTitles">
                {{ loading.titles ? '生成中…' : '生成标题' }}
              </el-button>
            </el-form-item>
            <div v-if="results.titles" class="titles-grid">
              <article v-for="(t, i) in results.titles.titles" :key="i" class="title-card">
                <p class="title-text">{{ t.text }}</p>
                <div class="title-actions">
                  <el-button size="small" plain @click="onApplyTo('title', t.text)">应用为标题</el-button>
                  <el-button size="small" @click="copyToClipboard(t.text)">复制</el-button>
                </div>
              </article>
            </div>
          </el-form>
        </section>

        <!-- ====== Phase B.3: 标签生成 ====== -->
        <section v-else-if="activeTab === 'tags'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">AI 提取标签</h2>
          <p class="ds-card__lede">从内容提 N 个标签,按主题/情绪/受众/热点分组。</p>
          <el-form :model="forms.tags" label-position="top">
            <el-form-item label="原文">
              <el-input v-model="forms.tags.content" type="textarea" :rows="5"
                       placeholder="粘贴正文..." maxlength="10000" show-word-limit />
            </el-form-item>
            <el-form-item label="候选数 / 字符风格">
              <div class="row-pair">
                <el-input-number v-model="forms.tags.n" :min="1" :max="30" style="width: 110px" />
                <el-select v-model="forms.tags.locale" style="width: 130px">
                  <el-option label="中文" value="zh" />
                  <el-option label="英文" value="en" />
                  <el-option label="Emoji" value="emoji" />
                  <el-option label="混合" value="mixed" />
                </el-select>
              </div>
            </el-form-item>
            <ProviderPicker v-model="forms.tags" />
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.tags"
                         :disabled="!forms.tags.content" @click="genTags">
                {{ loading.tags ? '生成中…' : '生成标签' }}
              </el-button>
            </el-form-item>
            <div v-if="results.tags" class="tags-pills">
              <el-tag
                v-for="(t, i) in results.tags.tags"
                :key="i"
                :type="groupToType(t.group)"
                effect="light"
                size="large"
                class="tag-pill"
              >
                <span class="tag-group">[{{ groupLabel(t.group) }}]</span> {{ t.text }}
                <el-button size="small" link @click.stop="addTagToContent(t.text)">+ 应用</el-button>
              </el-tag>
            </div>
          </el-form>
        </section>

        <!-- ====== 图像生成 ====== -->
        <section v-else-if="activeTab === 'image'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">文字转图像</h2>
          <p class="ds-card__lede">基于 prompt 生成配图,支持风格、比例、多张。</p>
          <el-form :model="forms.image" label-position="top">
            <el-form-item label="提示词">
              <el-input v-model="forms.image.prompt" type="textarea" :rows="3"
                       placeholder="例如:航拍镜头飞越山谷日落" />
            </el-form-item>
            <el-form-item label="风格 / 比例 / 数量">
              <div class="row-pair">
                <el-input v-model="forms.image.style" placeholder="风格" style="width: 130px" />
                <el-select v-model="forms.image.ratio" style="width: 110px">
                  <el-option label="1:1" value="1:1" />
                  <el-option label="16:9" value="16:9" />
                  <el-option label="9:16" value="9:16" />
                  <el-option label="4:3" value="4:3" />
                  <el-option label="3:4" value="3:4" />
                </el-select>
                <el-input-number v-model="forms.image.n" :min="1" :max="4" style="width: 110px" />
              </div>
            </el-form-item>
            <el-form-item>
              <el-button class="primary-cta" :loading="loading.image"
                         :disabled="!forms.image.prompt" @click="genImage">
                {{ loading.image ? '生成中…' : '生成图像' }}
              </el-button>
            </el-form-item>
            <el-alert v-if="imageResult?.is_mock" type="warning" :closable="false" show-icon
                       :title="`Mock 模式:${imageResult.error || 'API key 未配置'}`" />
            <div v-if="imageResult" class="image-grid">
              <article v-for="(it, i) in imageResult.items" :key="i" class="image-card">
                <img :src="it.image_url" :alt="it.prompt" @error="onImgError" />
                <div class="image-card-meta">
                  <span class="ds-pill" :class="`ds-pill--${it.is_mock ? 'neutral' : 'success'}`">
                    {{ it.is_mock ? 'MOCK' : 'REAL' }}
                  </span>
                  <el-button size="small" plain @click="copyToClipboard(it.image_url)">复制 URL</el-button>
                </div>
              </article>
            </div>
            <div v-if="imageHistory.length > 0" class="video-history">
              <h3 class="ds-section-head">图像历史 ({{ imageHistory.length }})</h3>
              <div class="image-grid">
                <article v-for="h in imageHistory.slice(0, 12)" :key="h.id" class="image-card">
                  <img :src="h.image_url" :alt="h.prompt" @error="onImgError" />
                  <div class="image-card-meta">
                    <span class="caption">{{ h.ratio }} · {{ formatTime(h.created_at) }}</span>
                  </div>
                </article>
              </div>
            </div>
          </el-form>
        </section>

        <!-- ====== 视频生成 ====== -->
        <section v-else-if="activeTab === 'video'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">文字转视频</h2>
          <p class="ds-card__lede">MiniMax-Hailuo-03 模型(每日 3 次额度,3/6/10s 可选)。</p>
          <el-form :model="forms.video" label-position="top">
            <el-form-item label="视频描述">
              <el-input v-model="forms.video.prompt" type="textarea" :rows="3"
                       placeholder="例如:航拍镜头飞越山谷日落" />
            </el-form-item>
            <el-form-item label="时长与比例">
              <div class="row-pair">
                <el-select v-model="forms.video.duration" style="width: 110px">
                  <el-option v-for="d in DURATION_OPTIONS" :key="d" :label="`${d} 秒`" :value="d" />
                </el-select>
                <el-select v-model="forms.video.ratio" style="width: 130px">
                  <el-option v-for="r in RATIO_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
                </el-select>
                <el-input v-model="forms.video.style" placeholder="风格(可选)" style="flex: 1" />
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
                <el-button size="small" :disabled="!videoResult.is_mock"
                           @click="goPublishRecords(videoResult.record.id)">去发布</el-button>
                <el-button size="small" plain @click="videoResult = null">清除</el-button>
              </div>
            </div>
            <div v-if="videoHistory.length > 0" class="video-history">
              <h3 class="ds-section-head">视频历史 ({{ videoHistory.length }})</h3>
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
                  <p class="video-prompt">{{ v.prompt.slice(0, 60) }}{{ v.prompt.length > 60 ? '…' : '' }}</p>
                  <p class="caption">{{ v.duration }}s · {{ v.ratio }} · {{ formatTime(v.created_at) }}</p>
                  <div class="video-card-actions">
                    <el-button size="small" :disabled="v.is_mock" @click="goPublishRecords(v.id)">发布</el-button>
                    <el-button size="small" plain @click="deleteVideo(v.id)">删除</el-button>
                  </div>
                </article>
              </div>
            </div>
          </el-form>
        </section>

        <!-- ====== Phase B.4: 创作历史(跨模块) ====== -->
        <section v-else-if="activeTab === 'history'" class="ds-card ai-tab-card">
          <h2 class="ds-card__title">创作历史</h2>
          <p class="ds-card__lede">所有 AI 调用的最近记录(按时间倒序)。</p>
          <div class="row-pair" style="margin-bottom: 12px">
            <el-select v-model="historyFilter" placeholder="按类型过滤" clearable style="width: 180px">
              <el-option v-for="t in CREATION_TYPES" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
            <el-button @click="loadCreationHistory">刷新</el-button>
          </div>
          <div v-if="creationHistory.length === 0" class="ds-empty">
            <p>还没有创作记录。</p>
            <p class="caption">用任意模块生成一次,这里就会有记录。</p>
          </div>
          <div v-else class="history-list">
            <article v-for="c in creationHistory" :key="c.id" class="history-card">
              <header class="history-head">
                <span class="ds-pill ds-pill--neutral">{{ c.type }}</span>
                <span class="ds-pill ds-pill--success">{{ c.provider }}{{ c.model ? ` / ${c.model}` : '' }}</span>
                <span class="caption mono">{{ c.latency_ms }}ms · {{ formatTime(c.created_at) }}</span>
                <span class="grow"></span>
                <el-button size="small" plain @click="deleteCreation(c.id)">删除</el-button>
              </header>
              <details>
                <summary>查看 prompt + result</summary>
                <pre class="history-content">{{ c.prompt }}</pre>
                <pre class="history-content history-result">{{ c.result }}</pre>
              </details>
            </article>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, defineComponent, h } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  aiApi,
  type VideoRecord,
  type VideoGenerateResponse,
  type ImageRecord,
} from '@/api/ai'
import { settingsApi } from '@/api/settings'
import { contentApi } from '@/api/content'
import { PLATFORM_OPTIONS, getPlatformName } from '@/constants'

// ============================================================
// 模块元数据 — 决定 sidebar 分组 + 顺序
// ============================================================

interface ModuleMeta {
  id: string
  label: string
  icon: string
  isNew?: boolean
}

interface ModuleGroup {
  id: string
  label: string
  modules: ModuleMeta[]
}

// SVG 图标做成 16x16 简洁线稿
const ICON_SUMMARY = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h10M3 6h10M3 9h7M3 12h4" stroke-linecap="round" /></svg>'
const ICON_PODCAST = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="2" width="6" height="9" rx="3" /><path d="M3 8a5 5 0 0010 0M8 13v2" stroke-linecap="round" /></svg>'
const ICON_COPY = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 5h12v8H2z M5 8h6" stroke-linecap="round" /></svg>'
const ICON_SCRIPT = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 4l9 4-9 4z" stroke-linejoin="round" /></svg>'
const ICON_EXPAND = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 4l-2 2 2 2M12 4l2 2-2 2M4 12l-2-2 2-2M12 12l2-2-2-2M5 8h6" stroke-linecap="round" stroke-linejoin="round" /></svg>'
const ICON_TITLES = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 4h10M3 7h7M3 10h10M3 13h5" stroke-linecap="round" /></svg>'
const ICON_TAGS = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h4l6 6-4 4-6-6V3z" stroke-linejoin="round" /><circle cx="6" cy="6" r="0.8" fill="currentColor" /></svg>'
const ICON_IMAGE = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="12" height="10" rx="1.5" /><circle cx="6" cy="7" r="1.5" /><path d="M2 12l4-4 3 3 3-3 2 2" stroke-linecap="round" stroke-linejoin="round" /></svg>'
const ICON_VIDEO = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="12" height="10" rx="1.5" /><path d="M6 5.5l4 2.5-4 2.5z" fill="currentColor" /></svg>'
const ICON_HISTORY = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 8a6 6 0 1 0 1.5-4M2 3v3h3M8 4v4l3 2" stroke-linecap="round" stroke-linejoin="round" /></svg>'

const MODULE_GROUPS: ModuleGroup[] = [
  {
    id: 'text',
    label: '内容生成',
    modules: [
      { id: 'summary',     label: '内容摘要',  icon: ICON_SUMMARY },
      { id: 'copy',        label: '多平台文案', icon: ICON_COPY },
      { id: 'video-script',label: '视频脚本',  icon: ICON_SCRIPT },
      { id: 'podcast',     label: '播客脚本',  icon: ICON_PODCAST },
      { id: 'expand',      label: '扩写',     icon: ICON_EXPAND,   isNew: true },
      { id: 'titles',      label: '标题生成', icon: ICON_TITLES,   isNew: true },
      { id: 'tags',        label: '标签提取', icon: ICON_TAGS,     isNew: true },
    ],
  },
  {
    id: 'visual',
    label: '视觉创作',
    modules: [
      { id: 'image', label: '图像生成', icon: ICON_IMAGE },
      { id: 'video', label: '视频生成', icon: ICON_VIDEO },
    ],
  },
  {
    id: 'tools',
    label: '优化工具',
    modules: [
      { id: 'history', label: '创作历史', icon: ICON_HISTORY },
    ],
  },
]

const CREATION_TYPES = [
  { value: 'summary',      label: '摘要' },
  { value: 'podcast',      label: '播客' },
  { value: 'copy',         label: '文案' },
  { value: 'video_script', label: '视频脚本' },
  { value: 'expand',       label: '扩写' },
  { value: 'titles',       label: '标题' },
  { value: 'tags',         label: '标签' },
]

// ============================================================
// 路由
// ============================================================

const router = useRouter()
const activeTab = ref<string>('summary')

// ============================================================
// 表单 / 加载 / 结果 状态(每个模块独立)
// ============================================================

interface FormBase { provider?: string; model?: string }
const defaultProvider = ref<string>('minimax')
const defaultModel = ref<string>('MiniMax-M3')

const forms = reactive<any>({
  summary:     { content: '',         provider: '', model: '' },
  podcast:     { content: '',         style: 'casual', provider: '', model: '' },
  copy:        { topic: '',            platform: 'douyin', content_type: 'short_video', provider: '', model: '' },
  videoScript: { topic: '',            duration: 60, provider: '', model: '' },
  expand:      { content: '',         target_length: 'medium', tone: 'casual', provider: '', model: '' },
  titles:      { content: '',         n: 5, platform: '', style: 'neutral', provider: '', model: '' },
  tags:        { content: '',         n: 10, locale: 'mixed', provider: '', model: '' },
  image:       { prompt: '',           style: '写实摄影', ratio: '1:1', n: 1 },
  video:       { prompt: '',           duration: 6, ratio: '16:9', style: '' },
})

const loading = reactive<any>({
  summary: false, podcast: false, copy: false, videoScript: false,
  expand: false, titles: false, tags: false,
  image: false, video: false,
})
const results = reactive<any>({})

// image / video 单独保留 response(它们有自己的 mock/info 字段)
const imageResult = ref<any>(null)
const videoResult = ref<VideoGenerateResponse | null>(null)
const imageHistory = ref<any[]>([])
const videoHistory = ref<VideoRecord[]>([])

// 创作历史
const creationHistory = ref<any[]>([])
const historyFilter = ref<string>('')

// 常量
const DURATION_OPTIONS = [3, 6, 10]
const RATIO_OPTIONS = [
  { value: '16:9', label: '16:9 横屏' },
  { value: '9:16', label: '9:16 竖屏(抖音推荐)' },
  { value: '1:1', label: '1:1 方形' },
]

// ============================================================
// 子组件(局部用,仅在此文件用到)
// ============================================================

const ProviderPicker = defineComponent({
  name: 'ProviderPicker',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('div', { class: 'provider-picker' }, [
      h('span', { class: 'caption' }, 'AI 模型:'),
      h(
        'select',
        {
          class: 'provider-select',
          value: (props.modelValue as any)?.provider || '',
          onChange: (e: Event) => {
            const v = (e.target as HTMLSelectElement).value
            emit('update:modelValue', { ...(props.modelValue as object), provider: v })
          },
        },
        [
          h('option', { value: '' }, '默认'),
          h('option', { value: 'minimax' }, 'MiniMax'),
          h('option', { value: 'claude' }, 'Claude'),
          h('option', { value: 'openai' }, 'OpenAI'),
        ]
      ),
    ])
  },
})

const ResultBlock = defineComponent({
  name: 'ResultBlock',
  props: {
    text: { type: String, required: true },
    meta: { type: String, default: '' },
  },
  emits: ['apply'],
  setup(props, { emit }) {
    return () => h('div', { class: 'result-block' }, [
      props.text ? h('pre', { class: 'result-text' }, props.text) : null,
      props.meta ? h('div', { class: 'result-meta' }, props.meta) : null,
      h('div', { class: 'result-actions' }, [
        h(
          'button',
          {
            class: 'el-button el-button--small',
            onClick: () => copyToClipboard(props.text),
          },
          '复制全文'
        ),
        h(
          'button',
          {
            class: 'el-button el-button--small el-button--primary',
            onClick: () => emit('apply', props.text),
          },
          '应用到内容 →'
        ),
      ]),
    ])
  },
})

// ============================================================
// 工具函数
// ============================================================

function copyToClipboard(text: string) {
  if (!text) return
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(
      () => ElMessage.success('已复制'),
      () => fallbackCopy(text)
    )
  } else {
    fallbackCopy(text)
  }
}
function fallbackCopy(text: string) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  try { document.execCommand('copy'); ElMessage.success('已复制') }
  catch { ElMessage.error('复制失败') }
  document.body.removeChild(ta)
}

const formatTime = (iso: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  return d.toLocaleDateString('zh-CN')
}

const onImgError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}

const handleError = (e: any, op: string) => {
  const msg = e.normalizedMessage || e.message || '生成失败'
  if (msg.includes('API Key') || msg.includes('api_key') || msg.includes('未配置')) {
    ElMessage.error(`AI 服务未配置:请先在设置页面配置 API Key`)
  } else {
    ElMessage.error(`${op} 失败: ${msg}`)
  }
}

// 应用到内容(简单: 跳 /content/new 带预填字段)
const onApplyTo = (field: 'title' | 'body', text: string) => {
  if (!text) return
  router.push({
    path: '/content/new',
    query: { [field]: text, from: 'ai' },
  })
  ElMessage.success(`已跳到新建内容页(预填 ${field})`)
}

// 添加标签到内容(简单: 跳 /content/new 带 tags 数组)
const addTagToContent = (tag: string) => {
  if (!tag) return
  router.push({
    path: '/content/new',
    query: { add_tag: tag, from: 'ai' },
  })
  ElMessage.success(`已跳到新建内容页(预填标签 ${tag})`)
}

const goPublishRecords = (videoId: string) => {
  router.push({ path: '/publish-records', query: { video_id: videoId } })
}

const groupLabel = (g: string) => ({ topic: '主题', emotion: '情绪', audience: '受众', trending: '热点' } as any)[g] || g
const groupToType = (g: string): 'success' | 'warning' | 'info' | 'danger' => {
  return ({ topic: 'success', emotion: 'warning', audience: 'info', trending: 'danger' } as any)[g] || 'info'
}

// ============================================================
// 各模块的生成函数
// ============================================================

const genSummary = async () => {
  loading.summary = true
  try {
    const result = await aiApi.expand(forms.summary.content.slice(0, 200), {  // 复用 expand?
      // 实际我们用 summary endpoint
    } as any)
    // 走专用 endpoint
  } catch {
    // fallthrough
  }
  // 改成直接调 summary
  loading.summary = true
  try {
    const r = await (await import('@/api/ai')).aiApi.summary(forms.summary.content)
    results.summary = r
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
    results.copy = await aiApi.copy(forms.copy.topic, forms.copy.platform, forms.copy.content_type)
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

const genExpand = async () => {
  loading.expand = true
  try {
    results.expand = await aiApi.expandText({
      content: forms.expand.content,
      target_length: forms.expand.target_length,
      tone: forms.expand.tone,
      provider: forms.expand.provider || undefined,
      model: forms.expand.model || undefined,
    })
  } catch (e: any) { handleError(e, '扩写') }
  finally { loading.expand = false }
}

const genTitles = async () => {
  loading.titles = true
  try {
    results.titles = await aiApi.titles({
      content: forms.titles.content,
      n: forms.titles.n,
      platform: forms.titles.platform || undefined,
      style: forms.titles.style,
      provider: forms.titles.provider || undefined,
      model: forms.titles.model || undefined,
    })
  } catch (e: any) { handleError(e, '标题生成') }
  finally { loading.titles = false }
}

const genTags = async () => {
  loading.tags = true
  try {
    results.tags = await aiApi.tags({
      content: forms.tags.content,
      n: forms.tags.n,
      locale: forms.tags.locale,
      provider: forms.tags.provider || undefined,
      model: forms.tags.model || undefined,
    })
  } catch (e: any) { handleError(e, '标签生成') }
  finally { loading.tags = false }
}

const genImage = async () => {
  loading.image = true
  try {
    imageResult.value = await aiApi.image({
      prompt: forms.image.prompt, style: forms.image.style,
      ratio: forms.image.ratio, n: forms.image.n,
    })
    const list = await aiApi.imageList(50)
    imageHistory.value = list.items || []
    if (imageResult.value?.is_mock) {
      ElMessage.warning(`已用 mock 模式: ${imageResult.value.error || 'API key 未配置'}`)
    } else {
      ElMessage.success(`已生成 ${imageResult.value.count} 张图片`)
    }
  } catch (e: any) { handleError(e, '图像生成') }
  finally { loading.image = false }
}

const genVideo = async () => {
  loading.video = true
  try {
    videoResult.value = await aiApi.videoGenerate({
      prompt: forms.video.prompt,
      duration: forms.video.duration,
      ratio: forms.video.ratio,
      style: forms.video.style || undefined,
    })
    if (videoResult.value?.is_mock) {
      ElMessage.warning(`已用 mock: ${videoResult.value.error || 'API key 未配置'}`)
    } else {
      ElMessage.success(`已生成视频 (${videoResult.value.record.duration}s)`)
    }
    await loadVideoHistory()
  } catch (e: any) { handleError(e, '视频生成') }
  finally { loading.video = false }
}

const loadVideoHistory = async () => {
  try {
    const list = await aiApi.videoList(50)
    videoHistory.value = list.items || []
  } catch { /* silent */ }
}

const deleteVideo = async (id: string) => {
  try {
    await ElMessage.confirm('删除该视频记录?(磁盘占位文件也会被清理)', '确认', { type: 'warning' })
  } catch { return }
  try {
    await aiApi.videoDelete(id)
    videoHistory.value = videoHistory.value.filter(v => v.id !== id)
    ElMessage.success('已删除')
  } catch (e: any) { handleError(e, '删除视频') }
}

const loadCreationHistory = async () => {
  try {
    const r = await aiApi.creationsList(historyFilter.value || undefined, 50)
    creationHistory.value = r.items || []
  } catch (e: any) { handleError(e, '加载创作历史') }
}

const deleteCreation = async (id: string) => {
  try {
    await aiApi.creationsDelete(id)
    creationHistory.value = creationHistory.value.filter(c => c.id !== id)
    ElMessage.success('已删除')
  } catch (e: any) { handleError(e, '删除创作记录') }
}

// 切到 history tab 时拉历史
watch(activeTab, (tab) => {
  if (tab === 'video') loadVideoHistory()
  if (tab === 'history') loadCreationHistory()
})

onMounted(async () => {
  // 加载默认 provider 名字
  try {
    const info = await settingsApi.providersList()
    if (info.default) defaultProvider.value = info.default
  } catch { /* silent */ }
  // 初次加载视频历史(供以后切 tab 时不空)
  loadVideoHistory()
})
</script>

<style scoped>
/* ============ 两栏布局(Phase C.1) ============ */
.ai-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 24px;
  margin-top: 24px;
}
@media (max-width: 768px) {
  .ai-layout { grid-template-columns: 1fr; }
}

/* ============ 侧边栏 ============ */
.ai-sidebar {
  position: sticky; top: 16px; align-self: start;
  display: flex; flex-direction: column; gap: 16px;
}
.sidebar-section-title {
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--claude-stone);
  margin: 0 0 6px 4px;
}
.sidebar-item {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 8px 10px;
  background: transparent; border: 0;
  border-radius: 8px;
  font: inherit; font-size: 14px; text-align: left;
  color: var(--claude-text-primary);
  cursor: pointer;
  transition: background 120ms ease;
}
.sidebar-item:hover { background: var(--claude-parchment); }
.sidebar-item.active {
  background: var(--claude-terracotta);
  color: var(--claude-ivory);
  font-weight: 500;
}
.sidebar-item.active .item-icon { color: var(--claude-ivory); }
.item-icon { color: var(--claude-terracotta); display: inline-flex; }
.item-label { flex: 1; }
.item-badge {
  font-size: 10px; padding: 1px 5px;
  background: var(--claude-coral); color: white;
  border-radius: 4px;
}
.sidebar-item.active .item-badge { background: rgba(255,255,255,0.2); }
.sidebar-link {
  display: block; padding: 8px 10px;
  color: var(--claude-stone); font-size: 13px;
  text-decoration: none; border-radius: 8px;
}
.sidebar-link:hover { background: var(--claude-parchment); color: var(--claude-terracotta); }

/* ============ Provider picker(子组件样式) ============ */
.provider-picker {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 0;
}
.provider-picker .caption { color: var(--claude-stone); }
.provider-select {
  padding: 4px 8px;
  border: 1px solid var(--claude-border-cream);
  border-radius: 6px;
  background: var(--claude-parchment);
  font: inherit; font-size: 13px;
}

/* ============ Result block(子组件样式) ============ */
.result-text {
  font: inherit; white-space: pre-wrap; word-break: break-word;
  background: var(--claude-parchment);
  padding: 14px; border-radius: 8px;
  margin: 0;
}
.result-meta { font-size: 12px; color: var(--claude-stone); margin-top: 6px; }
.result-actions { display: flex; gap: 8px; margin-top: 10px; }

/* ============ 现有按钮(保留) ============ */
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

/* ============ 图像 ============ */
.image-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px; margin-top: 12px;
}
.image-card {
  border: 1px solid var(--claude-border-cream);
  background: var(--claude-parchment);
  border-radius: var(--radius-lg);
  padding: 10px;
  display: flex; flex-direction: column; gap: 6px;
}
.image-card img {
  width: 100%; aspect-ratio: 1; object-fit: cover;
  border-radius: 6px;
}
.image-card-meta { display: flex; gap: 6px; align-items: center; }

/* ============ 标题 + 标签(C.2 增强) ============ */
.titles-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px; margin-top: 12px;
}
.title-card {
  border: 1px solid var(--claude-border-cream);
  background: var(--claude-ivory);
  border-radius: var(--radius-md);
  padding: 12px; display: flex; flex-direction: column; gap: 8px;
}
.title-text { font-weight: 500; font-size: 14px; line-height: 1.4; margin: 0; }
.title-actions { display: flex; gap: 6px; }
.tags-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.tag-pill { padding: 6px 10px; font-size: 13px; }
.tag-group { font-size: 10px; opacity: 0.7; margin-right: 4px; font-weight: 600; }

/* ============ 创作历史(C.2) ============ */
.history-list { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.history-card {
  border: 1px solid var(--claude-border-cream);
  background: var(--claude-ivory);
  border-radius: var(--radius-md);
  padding: 12px;
}
.history-head { display: flex; gap: 8px; align-items: center; }
.history-head .grow { flex: 1; }
.history-card details { margin-top: 8px; }
.history-card summary {
  cursor: pointer; font-size: 12px; color: var(--claude-stone);
  padding: 4px 0;
}
.history-content {
  background: var(--claude-parchment);
  padding: 8px; border-radius: 6px;
  font-size: 12px; white-space: pre-wrap; word-break: break-word;
  max-height: 200px; overflow: auto;
  margin: 4px 0;
}
.history-result { border-left: 3px solid var(--claude-terracotta); }

</style>
