<template>
  <div class="material-page">
    <el-card class="material-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>🖼️</span>
            <span>素材库</span>
          </div>
          <el-upload
            action="#"
            :show-file-list="false"
            :before-upload="() => false"
            @change="handleUpload"
          >
            <el-button type="primary">+ 上传素材</el-button>
          </el-upload>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="filterByType" class="material-tabs">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="图片" name="image" />
        <el-tab-pane label="视频" name="video" />
        <el-tab-pane label="音频" name="audio" />
      </el-tabs>

      <el-row :gutter="20" class="material-grid">
        <el-col v-for="item in materials" :key="item.id" :span="6">
          <div class="material-item">
            <div class="material-preview">
              <img v-if="item.type === 'image'" :src="item.path" :alt="item.name" />
              <div v-else-if="item.type === 'video'" class="video-placeholder">
                <span>🎬</span>
              </div>
              <div v-else class="file-placeholder">
                <span>📄</span>
              </div>
            </div>
            <div class="material-info">
              <div class="material-name">{{ item.name }}</div>
              <div class="material-tags">
                <el-tag v-for="tag in item.tags" :key="tag" size="small" class="tag">
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <div v-if="materials.length === 0" class="empty-state">
        <span class="empty-icon">📂</span>
        <p>暂无素材</p>
        <p class="empty-hint">点击上方按钮上传素材</p>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const materials = ref<any[]>([])
const activeTab = ref('all')

const fetchMaterials = async (type?: string) => {
  try {
    const url = type && type !== 'all' ? `/api/cms/materials?type=${type}` : '/api/cms/materials'
    const res = await axios.get(url)
    materials.value = res.data
  } catch (error) {
    console.error('Failed to fetch materials:', error)
  }
}

const filterByType = (type: string) => {
  fetchMaterials(type === 'all' ? undefined : type)
}

const handleUpload = () => {
  ElMessage.info('素材上传功能开发中...')
}

onMounted(() => fetchMaterials())
</script>

<style scoped>
.material-page {
  padding: 0;
}

.material-card {
  background: rgba(26, 26, 46, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.material-grid {
  margin-top: 20px;
}

.material-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.material-item:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.3);
}

.material-preview {
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
}

.material-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
}

.video-placeholder,
.file-placeholder {
  font-size: 40px;
  opacity: 0.5;
}

.material-info {
  padding: 12px;
}

.material-name {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.material-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag {
  background: rgba(0, 212, 255, 0.1);
  border: none;
  color: #00d4ff;
  font-size: 10px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-icon {
  font-size: 60px;
  opacity: 0.5;
}

.empty-hint {
  font-size: 12px;
  color: #444;
  margin-top: 8px;
}
</style>