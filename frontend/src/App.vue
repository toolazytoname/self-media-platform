<template>
  <!-- 登录页不使用侧边栏布局 -->
  <router-view v-if="$route.meta?.hideLayout" />

  <div v-else class="app-container">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          <span class="logo-icon">📱</span>
          <span class="logo-text">自媒体平台</span>
        </div>

        <el-menu
          :default-active="$route.path"
          router
          class="sidebar-menu"
          background-color="#1a1a2e"
          text-color="#a0a0b0"
          active-text-color="#00d4ff"
        >
          <el-menu-item index="/content">
            <span class="menu-icon">📝</span>
            <span>内容管理</span>
          </el-menu-item>
          <el-menu-item index="/topic">
            <span class="menu-icon">💡</span>
            <span>选题库</span>
          </el-menu-item>
          <el-menu-item index="/material">
            <span class="menu-icon">🖼️</span>
            <span>素材库</span>
          </el-menu-item>
          <el-menu-item index="/review">
            <span class="menu-icon">✅</span>
            <span>审核</span>
          </el-menu-item>
          <el-menu-item index="/templates">
            <span class="menu-icon">📋</span>
            <span>内容模板</span>
          </el-menu-item>
          <el-menu-item index="/platform">
            <span class="menu-icon">🌐</span>
            <span>平台</span>
          </el-menu-item>
          <el-menu-item index="/publish-records">
            <span class="menu-icon">📤</span>
            <span>发布记录</span>
          </el-menu-item>
          <el-menu-item index="/ai">
            <span class="menu-icon">🤖</span>
            <span>AI 生成</span>
          </el-menu-item>
          <el-menu-item index="/stats">
            <span class="menu-icon">📊</span>
            <span>数据统计</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <span class="menu-icon">⚙️</span>
            <span>设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <!-- 顶部 -->
        <el-header class="header">
          <div class="header-left">
            <h2 class="page-title">{{ pageTitle }}</h2>
          </div>
          <div class="header-right">
            <el-button type="primary" class="create-btn" @click="createContent">
              <span>+ 创建内容</span>
            </el-button>
            <el-dropdown trigger="click" @command="onUserCmd">
              <div class="user-avatar">
                <span>{{ userInitial }}</span>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item disabled>
                    <div class="user-info">
                      <div class="user-name">{{ user?.display_name || user?.username }}</div>
                      <div class="user-username">@{{ user?.username }}</div>
                    </div>
                  </el-dropdown-item>
                  <el-dropdown-item divided command="settings">
                    <span>⚙️ 系统设置</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="logout">
                    <span>🚪 退出登录</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <!-- 主内容 -->
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
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
  if (!u) return '👤'
  return (u.display_name || u.username).charAt(0).toUpperCase()
})

const pageTitleMap: Record<string, string> = {
  '/content': '内容管理',
  '/content/create': '创建内容',
  '/topic': '选题库',
  '/material': '素材库',
  '/review': '审核',
  '/templates': '内容模板',
  '/platform': '平台管理',
  '/publish-records': '发布记录',
  '/ai': 'AI 生成',
  '/stats': '数据统计',
  '/settings': '系统设置',
}

const pageTitle = computed(() => {
  if (route.path.startsWith('/content/edit/')) return '编辑内容'
  if (route.path.startsWith('/content/view/')) return '内容详情'
  return pageTitleMap[route.path] || '内容管理'
})

const createContent = () => {
  router.push('/content/create')
}

const onUserCmd = (cmd: string) => {
  if (cmd === 'settings') {
    router.push('/settings')
  } else if (cmd === 'logout') {
    clearAuth()
    user.value = null
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}

onMounted(() => {
  user.value = getStoredUser()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app-container {
  height: 100vh;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f0f1a;
}

.el-container {
  height: 100%;
}

/* 侧边栏 */
.sidebar {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
}

.logo {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  letter-spacing: -0.5px;
}

.sidebar-menu {
  border: none;
  background: transparent;
}

.sidebar-menu .el-menu-item {
  height: 52px;
  line-height: 52px;
  margin: 4px 12px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding-left: 16px !important;
  transition: all 0.3s ease;
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(0, 212, 255, 0.1);
  color: #00d4ff;
}

.sidebar-menu .el-menu-item.is-active {
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.2) 0%, rgba(0, 212, 255, 0.05) 100%);
  color: #00d4ff;
  border-right: 3px solid #00d4ff;
}

.menu-icon {
  font-size: 18px;
}

/* 顶部 */
.header {
  background: rgba(26, 26, 46, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 32px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  letter-spacing: -0.5px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.create-btn {
  background: linear-gradient(135deg, #00d4ff 0%, #00a8cc 100%);
  border: none;
  padding: 12px 24px;
  border-radius: 10px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.create-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 212, 255, 0.3);
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  transition: all 0.3s ease;
}

.user-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.user-info {
  padding: 4px 0;
  min-width: 160px;
}

.user-name {
  font-size: 14px;
  color: #fff;
  font-weight: 600;
}

.user-username {
  font-size: 12px;
  color: #a0a0b0;
  margin-top: 2px;
}

/* 主内容 */
.main-content {
  background: #0f0f1a;
  padding: 24px 32px;
}

/* 全局 Element Plus 覆盖 */
.el-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  backdrop-filter: blur(20px);
}

.el-table {
  background: transparent;
  color: #e0e0e0;
}

.el-table th {
  background: rgba(0, 212, 255, 0.05);
  color: #00d4ff;
  font-weight: 500;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.el-table tr {
  background: transparent;
  transition: background 0.3s ease;
}

.el-table tr:hover {
  background: rgba(0, 212, 255, 0.05);
}

.el-table td {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.el-button {
  border-radius: 8px;
}

.el-button--primary {
  background: linear-gradient(135deg, #00d4ff 0%, #00a8cc 100%);
  border: none;
}

.el-button--danger {
  background: linear-gradient(135deg, #ff4757 0%, #ff6b81 100%);
  border: none;
}

.el-tag {
  border-radius: 6px;
  padding: 4px 10px;
}

.el-input__wrapper {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  box-shadow: none;
}

.el-input__wrapper:hover,
.el-input__wrapper.is-focus {
  border-color: #00d4ff;
}

.el-select__wrapper {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: none;
}

.el-dialog {
  background: #1a1a2e;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.el-dialog__title {
  color: #fff;
}

.el-tabs__item {
  color: #a0a0b0;
}

.el-tabs__item.is-active {
  color: #00d4ff;
}

.el-tabs__active-bar {
  background: #00d4ff;
}
</style>
