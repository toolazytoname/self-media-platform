<template>
  <div class="create-page">
    <el-card class="create-card">
      <template #header>
        <div class="card-header">
          <el-button text @click="$router.back()" class="back-btn">
            ← 返回
          </el-button>
          <span class="title">创建内容</span>
        </div>
      </template>

      <el-form :model="form" label-position="top" class="content-form">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="输入有吸引力的标题" size="large" />
        </el-form-item>

        <el-form-item label="内容" required>
          <el-input
            v-model="form.body"
            type="textarea"
            :rows="12"
            placeholder="输入内容正文..."
            class="content-textarea"
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="标签">
              <el-select v-model="form.tags" multiple placeholder="选择标签" style="width: 100%">
                <el-option label="科技" value="tech" />
                <el-option label="生活" value="life" />
                <el-option label="财经" value="finance" />
                <el-option label="娱乐" value="entertainment" />
                <el-option label="教育" value="education" />
                <el-option label="美食" value="food" />
                <el-option label="旅游" value="travel" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标平台">
              <el-select v-model="form.platform" placeholder="选择平台" style="width: 100%">
                <el-option label="全部平台" value="all" />
                <el-option label="抖音" value="douyin" />
                <el-option label="B站" value="bilibili" />
                <el-option label="小红书" value="xiaohongshu" />
                <el-option label="头条号" value="toutiao" />
                <el-option label="公众号" value="wechat" />
                <el-option label="YouTube" value="youtube" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <div class="form-actions">
          <el-button @click="$router.back()">取消</el-button>
          <el-button type="primary" @click="submit" :loading="submitting">
            创建内容
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const submitting = ref(false)
const form = ref({
  title: '',
  body: '',
  tags: [] as string[],
  platform: 'all'
})

const submit = async () => {
  if (!form.value.title || !form.value.body) {
    ElMessage.warning('请填写标题和内容')
    return
  }

  submitting.value = true
  try {
    await axios.post('/api/content/', form.value)
    ElMessage.success('创建成功')
    router.push('/content')
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.create-page {
  max-width: 900px;
}

.create-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  color: #00d4ff;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.content-form {
  padding: 20px 0;
}

.content-textarea {
  font-size: 15px;
  line-height: 1.8;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  margin-top: 24px;
}
</style>