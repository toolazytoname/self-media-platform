// 组件测试：Templates 页面
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

vi.mock('@/api/templates', () => ({
  templateApi: {
    list: vi.fn().mockResolvedValue([
      { id: 't1', name: '文章模板', category: 'article', description: 'desc', body: '# H' },
    ]),
    create: vi.fn().mockResolvedValue({ id: 't2' }),
    update: vi.fn().mockResolvedValue({ id: 't1' }),
    delete: vi.fn().mockResolvedValue({ message: 'ok', id: 't1' }),
  },
}))

vi.mock('@/api/content', () => ({
  contentApi: {
    create: vi.fn().mockResolvedValue({ id: 'c1', title: 'X' }),
  },
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
    ElMessageBox: { confirm: vi.fn().mockResolvedValue('ok') },
  }
})

import Templates from '@/views/Templates/index.vue'

const createWrapper = async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/templates', component: Templates },
      { path: '/content/edit/:id', component: { template: '<div>Edit</div>' } },
    ],
  })
  await router.push('/templates')
  await router.isReady()
  return mount(Templates, {
    global: {
      plugins: [router],
    },
  })
}

describe('Templates page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders template list', async () => {
    const wrapper = await createWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('文章模板')
  })

  it('shows "暂无模板" when empty', async () => {
    const { templateApi } = await import('@/api/templates')
    ;(templateApi.list as any).mockResolvedValueOnce([])
    const wrapper = await createWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('暂无模板')
  })

  it('opens create dialog when button clicked', async () => {
    const wrapper = await createWrapper()
    await flushPromises()
    const buttons = wrapper.findAll('button')
    // 找到 "新建模板" 按钮（包含 + 符号）
    const createBtn = buttons.find(b => b.text().includes('新建模板'))
    expect(createBtn).toBeDefined()
    await createBtn!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('新建模板')
  })
})
