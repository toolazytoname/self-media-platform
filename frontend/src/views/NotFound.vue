<template>
  <div class="not-found">
    <div class="frame">
      <div class="big">404</div>
      <h1>这页没找到</h1>
      <p>你访问的页面可能不存在、被移除，或者链接拼错了。</p>
      <div class="actions">
        <el-button @click="$router.back()">返回上页</el-button>
        <el-button type="primary" @click="$router.push('/content')">回首页</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  min-height: calc(100vh - 200px);
  display: flex; align-items: center; justify-content: center;
  padding: 48px 24px;
}
.frame {
  text-align: center;
  max-width: 480px;
}
.big {
  font-family: var(--font-serif);
  font-size: 140px; font-weight: 500;
  color: var(--claude-terracotta);
  line-height: 1;
  letter-spacing: -0.04em;
  margin-bottom: 16px;
}
h1 {
  font-family: var(--font-serif);
  font-size: 28px; font-weight: 500;
  color: var(--claude-ink);
  margin: 0 0 12px;
  letter-spacing: -0.015em;
}
p {
  font-size: 16px; color: var(--claude-olive);
  line-height: 1.55; margin: 0 0 24px;
}
.actions { display: flex; gap: 12px; justify-content: center; }
</style>
