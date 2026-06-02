// 组件测试：App.vue
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'

// mock element-plus icons
vi.mock('@element-plus/icons-vue', () => ({}))
// mock constants
vi.mock('@/constants', () => ({
  CONTENT_STATUSES: [],
  PLATFORM_OPTIONS: [],
  TAG_PRESETS: [],
  getStatusMeta: () => ({ label: '', tagType: '' }),
  getPlatformName: (v: string) => v,
  getPlatformIcon: () => '📱',
  formatDate: (d: string) => d,
  truncate: (s: string) => s,
}))

import App from '@/App.vue'

const routes = [
  { path: '/', redirect: '/content' },
  { path: '/content', component: { template: '<div class="content">Content</div>' } },
  { path: '/login', component: { template: '<div class="login">Login</div>' }, meta: { hideLayout: true } },
  { path: '/settings', component: { template: '<div>Settings</div>' } },
]

const createWrapper = async (initialPath = '/content') => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes,
  })
  await router.push(initialPath)
  await router.isReady()
  return mount(App, {
    global: {
      plugins: [router, createPinia()],
    },
  })
}

describe('App.vue', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders sidebar when not on login page', async () => {
    const wrapper = await createWrapper('/content')
    expect(wrapper.find('.sidebar').exists()).toBe(true)
  })

  it('hides sidebar on login page', async () => {
    const wrapper = await createWrapper('/login')
    // wait for next tick
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.sidebar').exists()).toBe(false)
  })

  it('shows page title from route', async () => {
    const wrapper = await createWrapper('/content')
    expect(wrapper.text()).toContain('内容管理')
  })

  it('has create button', async () => {
    const wrapper = await createWrapper('/content')
    const btn = wrapper.find('.create-btn')
    expect(btn.exists()).toBe(true)
  })
})
