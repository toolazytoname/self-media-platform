<template>
  <div class="not-found">
    <div class="content">
      <div class="big">404</div>
      <h1>页面未找到</h1>
      <p>您访问的页面不存在或已被移除</p>
      <el-button type="primary" @click="$router.push('/content')" size="large">
        返回首页
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
// 404 page
</script>

<style scoped>
.not-found {
  height: calc(100vh - 100px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.content {
  text-align: center;
  color: #fff;
}

.big {
  font-size: 120px;
  font-weight: 700;
  background: linear-gradient(135deg, #00d4ff 0%, #00a8cc 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
  margin-bottom: 16px;
}

h1 {
  font-size: 24px;
  margin-bottom: 8px;
  color: #fff;
}

p {
  color: #888;
  margin-bottom: 24px;
}
</style>
