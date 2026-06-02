// Vitest 测试设置
import { config } from '@vue/test-utils'
import ElementPlus from 'element-plus'

// 全局注册 Element Plus
config.global.plugins = [ElementPlus]
