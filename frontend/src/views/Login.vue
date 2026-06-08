<template>
  <div class="login-page">
    <!-- Parchment background, no gradients, no decorative blobs -->
    <div class="login-frame">
      <header class="brand">
        <div class="glyph">S</div>
        <h1>Self-Media Platform</h1>
        <p>AI 驱动的内容创作与多平台分发</p>
      </header>

      <section class="login-card">
        <div class="card-eyebrow">登录或注册</div>
        <h2 class="card-title">欢迎回来</h2>
        <p class="card-lede">用你的账号继续创作。密码至少 6 位，新账号 3 秒内可用。</p>

        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="登录" name="login">
            <el-form :model="loginForm" label-position="top" @keyup.enter="onLogin">
              <el-form-item label="用户名">
                <el-input v-model="loginForm.username" placeholder="请输入用户名" size="large" :prefix-icon="User" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" :prefix-icon="Lock" show-password />
              </el-form-item>
              <el-button type="primary" size="large" :loading="loading" class="primary-cta" @click="onLogin">
                {{ loading ? '登录中…' : '登录' }}
              </el-button>
              <div class="login-hint">
                还没有账号？<el-link type="primary" @click="activeTab = 'register'">立即注册</el-link>
              </div>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form :model="regForm" label-position="top" @keyup.enter="onRegister">
              <el-form-item label="用户名">
                <el-input v-model="regForm.username" placeholder="3-32 个字符" size="large" :prefix-icon="User" />
              </el-form-item>
              <el-form-item label="昵称（可选）">
                <el-input v-model="regForm.display_name" placeholder="显示名称" size="large" :prefix-icon="UserFilled" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="regForm.password" type="password" placeholder="至少 6 个字符" size="large" :prefix-icon="Lock" show-password />
              </el-form-item>
              <el-form-item label="确认密码">
                <el-input v-model="regForm.password2" type="password" placeholder="再次输入密码" size="large" :prefix-icon="Lock" show-password />
              </el-form-item>
              <el-button type="primary" size="large" :loading="loading" class="primary-cta" @click="onRegister">
                {{ loading ? '创建中…' : '注册' }}
              </el-button>
              <div class="login-hint">
                已有账号？<el-link type="primary" @click="activeTab = 'login'">去登录</el-link>
              </div>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </section>

      <footer class="footnote">
        Self-Media Platform · 基于 Claude × Apple 设计系统
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, UserFilled } from '@element-plus/icons-vue'
import { authApi, setAuth, getStoredUser } from '@/api/auth'

const router = useRouter()
const activeTab = ref<'login' | 'register'>('login')
const loading = ref(false)

const loginForm = ref({ username: '', password: '' })
const regForm = ref({ username: '', password: '', password2: '', display_name: '' })

const onLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    const resp = await authApi.login(loginForm.value.username, loginForm.value.password)
    setAuth(resp.access_token, resp.user)
    ElMessage.success(`欢迎回来, ${resp.user.display_name || resp.user.username}`)
    router.push('/content')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

const onRegister = async () => {
  if (!regForm.value.username || !regForm.value.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  if (regForm.value.password.length < 6) {
    ElMessage.warning('密码至少 6 个字符')
    return
  }
  if (regForm.value.password !== regForm.value.password2) {
    ElMessage.warning('两次密码不一致')
    return
  }
  loading.value = true
  try {
    const resp = await authApi.register(regForm.value.username, regForm.value.password, regForm.value.display_name)
    setAuth(resp.access_token, resp.user)
    ElMessage.success('注册成功，已登录')
    router.push('/content')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}

if (getStoredUser()) {
  router.push('/content')
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: var(--claude-parchment);
  display: flex; align-items: center; justify-content: center;
  padding: 48px 24px;
}
.login-frame {
  width: 100%; max-width: 440px;
  display: flex; flex-direction: column; gap: 32px;
}

.brand {
  text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.brand .glyph {
  width: 56px; height: 56px; border-radius: 16px;
  background: linear-gradient(135deg, var(--claude-terracotta), var(--claude-coral));
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-serif); font-size: 28px; font-weight: 500; color: var(--claude-ivory);
  margin-bottom: 8px;
}
.brand h1 {
  font-family: var(--font-serif);
  font-size: 28px; font-weight: 500;
  color: var(--claude-ink);
  margin: 0; letter-spacing: -0.01em;
}
.brand p {
  font-size: 15px; color: var(--claude-olive);
  margin: 0;
}

.login-card {
  background: var(--claude-ivory);
  border: 1px solid var(--claude-border-cream);
  border-radius: 20px;
  padding: 40px 36px 32px;
  box-shadow: 0 4px 24px rgba(20, 20, 19, 0.04);
}
.card-eyebrow {
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.10em;
  color: var(--claude-stone); font-weight: 500;
  margin-bottom: 8px;
}
.card-title {
  font-family: var(--font-serif);
  font-size: 32px; font-weight: 500;
  color: var(--claude-ink);
  margin: 0 0 8px;
  letter-spacing: -0.015em;
}
.card-lede {
  font-size: 15px; color: var(--claude-olive);
  margin: 0 0 24px; line-height: 1.55;
}

.login-tabs {
  margin-top: 8px;
}
.login-tabs :deep(.el-tabs__header) { margin-bottom: 24px; }
.login-tabs :deep(.el-tabs__item) {
  font-size: 15px; font-weight: 500;
  height: 44px; line-height: 44px;
  padding: 0 18px;
}

.primary-cta {
  width: 100%; margin-top: 8px;
  background: var(--claude-terracotta) !important;
  border: 0 !important; color: var(--claude-ivory) !important;
  border-radius: 12px !important;
  height: 46px !important; font-size: 15px !important; font-weight: 500 !important;
}
.primary-cta:hover { background: var(--claude-coral) !important; }

.login-hint {
  text-align: center; margin-top: 18px;
  font-size: 13px; color: var(--claude-stone);
}

.footnote {
  text-align: center;
  font-size: 12px; color: var(--claude-stone);
  letter-spacing: 0.04em;
}

@media (max-width: 480px) {
  .login-page { padding: 24px 16px; }
  .login-card { padding: 28px 24px 24px; }
  .card-title { font-size: 26px; }
}
</style>
