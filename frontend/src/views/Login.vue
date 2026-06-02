<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-blob blob-1"></div>
      <div class="bg-blob blob-2"></div>
      <div class="bg-blob blob-3"></div>
    </div>
    <div class="login-container">
      <div class="login-brand">
        <div class="brand-icon">📱</div>
        <h1>自媒体内容平台</h1>
        <p>AI 驱动 · 多平台分发 · 一键搞定</p>
      </div>

      <el-card class="login-card">
        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="登录" name="login">
            <el-form :model="loginForm" label-position="top" @keyup.enter="onLogin">
              <el-form-item label="用户名">
                <el-input v-model="loginForm.username" placeholder="请输入用户名" size="large" :prefix-icon="User" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" :prefix-icon="Lock" show-password />
              </el-form-item>
              <el-button type="primary" size="large" :loading="loading" style="width: 100%; margin-top: 8px" @click="onLogin">
                登 录
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
              <el-button type="primary" size="large" :loading="loading" style="width: 100%; margin-top: 8px" @click="onRegister">
                注 册
              </el-button>
              <div class="login-hint">
                已有账号？<el-link type="primary" @click="activeTab = 'login'">去登录</el-link>
              </div>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </el-card>
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
    const res = await authApi.login(loginForm.value)
    setAuth(res.access_token, res.user)
    ElMessage.success('登录成功')
    router.push('/content')
  } catch (e: any) {
    ElMessage.error(e.normalizedMessage || '登录失败')
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
    const res = await authApi.register({
      username: regForm.value.username,
      password: regForm.value.password,
      display_name: regForm.value.display_name || undefined,
    })
    setAuth(res.access_token, res.user)
    ElMessage.success('注册成功并已登录')
    router.push('/content')
  } catch (e: any) {
    ElMessage.error(e.normalizedMessage || '注册失败')
  } finally {
    loading.value = false
  }
}

// 已登录直接跳过
if (getStoredUser()) {
  router.replace('/content')
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f0f1a;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
}

.blob-1 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #00d4ff 0%, #0066ff 100%);
  top: -100px;
  left: -100px;
}

.blob-2 {
  width: 350px;
  height: 350px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  bottom: -100px;
  right: -100px;
}

.blob-3 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 0 20px;
}

.login-brand {
  text-align: center;
  margin-bottom: 32px;
  color: #fff;
}

.brand-icon {
  font-size: 56px;
  margin-bottom: 8px;
}

.login-brand h1 {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
  margin-bottom: 4px;
}

.login-brand p {
  font-size: 14px;
  color: #a0a0b0;
}

.login-card {
  background: rgba(26, 26, 46, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
}

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 24px;
}

.login-tabs :deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 500;
  color: #a0a0b0;
  height: 48px;
  line-height: 48px;
}

.login-tabs :deep(.el-tabs__item.is-active) {
  color: #00d4ff;
}

.login-tabs :deep(.el-tabs__active-bar) {
  background: #00d4ff;
}

.login-hint {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: #a0a0b0;
}
</style>
