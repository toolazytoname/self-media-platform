<template>
  <router-view v-if="$route.meta?.hideLayout" />

  <div v-else class="app-container">
    <!-- Apple-style top nav -->
    <header class="app-topnav">
      <router-link to="/content" class="brand">
        <span class="glyph">S</span>
        <span>Self-Media Platform</span>
      </router-link>

      <nav class="nav-links">
        <router-link
          v-for="link in topNav"
          :key="link.to"
          :to="link.to"
          :class="{ active: isActiveTop(link.to) }"
        >{{ link.label }}</router-link>
      </nav>

      <div class="nav-actions">
        <input class="search" type="text" placeholder="搜索..." />
        <div class="user-pill" @click="onUserClick">
          <span class="avatar">{{ userInitial }}</span>
          <span>{{ user?.display_name || user?.username || '登录' }}</span>
        </div>
      </div>
    </header>

    <div class="app-body">
      <!-- Claude-style sidebar (warm dark) -->
      <aside class="app-sidebar">
        <div class="section-label">内容</div>
        <nav>
          <router-link to="/content" :class="{ active: $route.path.startsWith('/content') }">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="14" height="14" rx="2" />
                <path d="M7 7h6M7 10h6M7 13h4" stroke-linecap="round" />
              </svg>
            </span>
            <span>内容管理</span>
          </router-link>
          <router-link to="/topic">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M10 2v3M10 15v3M2 10h3M15 10h3M4.2 4.2l2.1 2.1M13.7 13.7l2.1 2.1M4.2 15.8l2.1-2.1M13.7 6.3l2.1-2.1" stroke-linecap="round" />
              </svg>
            </span>
            <span>选题库</span>
          </router-link>
          <router-link to="/material">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="14" height="14" rx="2" />
                <circle cx="8" cy="8" r="1.5" />
                <path d="M3 13l4-4 4 4 3-3 3 3" stroke-linejoin="round" />
              </svg>
            </span>
            <span>素材库</span>
          </router-link>
        </nav>

        <div class="section-label">AI 工具</div>
        <nav>
          <router-link to="/ai" :class="{ active: $route.path === '/ai' }">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M10 3l1.5 4h4l-3.2 2.4 1.2 4-3.5-2.5L6.5 13.4l1.2-4L4.5 7h4z" stroke-linejoin="round" />
              </svg>
            </span>
            <span>AI 生成</span>
          </router-link>
        </nav>

        <div class="section-label">工作流</div>
        <nav>
          <router-link to="/review">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M4 10l3 3 9-9" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span>审核</span>
          </router-link>
          <router-link to="/templates">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="14" height="14" rx="1" />
                <path d="M3 8h14M8 8v9" />
              </svg>
            </span>
            <span>内容模板</span>
          </router-link>
          <router-link to="/platform">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="10" cy="10" r="7.5" />
                <path d="M2.5 10h15M10 2.5c2.5 2.5 2.5 12.5 0 15M10 2.5c-2.5 2.5-2.5 12.5 0 15" />
              </svg>
            </span>
            <span>平台账号</span>
          </router-link>
          <router-link to="/publish-records">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M4 12V6a1 1 0 011-1h10a1 1 0 011 1v6M4 12h12M4 12v4M16 12v4M7 16h6" stroke-linecap="round" />
              </svg>
            </span>
            <span>发布记录</span>
          </router-link>
        </nav>

        <div class="section-label">系统</div>
        <nav>
          <router-link to="/stats">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M3 17h14M6 13V8M10 13V5M14 13v-3" stroke-linecap="round" />
              </svg>
            </span>
            <span>数据</span>
          </router-link>
          <router-link to="/settings">
            <span class="icon">
              <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="10" cy="10" r="2.5" />
                <path d="M10 3v2M10 15v2M3 10h2M15 10h2M5 5l1.4 1.4M13.6 13.6L15 15M5 15l1.4-1.4M13.6 6.4L15 5" stroke-linecap="round" />
              </svg>
            </span>
            <span>设置</span>
          </router-link>
        </nav>
      </aside>

      <main class="app-main">
        <div class="app-main-inner">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clearAuth, getStoredUser, type UserInfo } from '@/api/auth'

const route = useRoute()
const router = useRouter()

const user = ref<UserInfo | null>(null)

const userInitial = computed(() => {
  const u = user.value
  if (!u) return '·'
  return (u.display_name || u.username || '?').charAt(0).toUpperCase()
})

const topNav = [
  { to: '/content', label: '内容' },
  { to: '/ai', label: 'AI 工具' },
  { to: '/review', label: '审核' },
  { to: '/publish-records', label: '发布' },
  { to: '/stats', label: '数据' },
]

const isActiveTop = (path: string) => {
  if (path === '/ai') return route.path.startsWith('/ai')
  return route.path.startsWith(path)
}

const onUserClick = () => {
  if (!user.value) {
    router.push('/login')
  } else {
    ElMessage.info('点击右上头像查看菜单（待接入）')
  }
}

onMounted(() => {
  user.value = getStoredUser()
})
</script>
