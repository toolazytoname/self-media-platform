// 常量与工具函数测试
import { describe, it, expect } from 'vitest'
import {
  CONTENT_STATUSES,
  PLATFORM_OPTIONS,
  TAG_PRESETS,
  getStatusMeta,
  getPlatformName,
  getPlatformIcon,
  formatDate,
  truncate,
} from '@/constants'

describe('CONTENT_STATUSES', () => {
  it('contains expected statuses', () => {
    const values = CONTENT_STATUSES.map(s => s.value)
    expect(values).toContain('draft')
    expect(values).toContain('pending')
    expect(values).toContain('published')
    expect(values).toContain('failed')
    expect(values).toContain('archived')
  })

  it('getStatusMeta returns meta for valid status', () => {
    const meta = getStatusMeta(CONTENT_STATUSES, 'draft')
    expect(meta).toBeDefined()
    expect(meta.label).toBeTruthy()
    expect(meta.tagType).toBeTruthy()
  })

  it('getStatusMeta returns fallback for unknown', () => {
    const meta = getStatusMeta(CONTENT_STATUSES, 'unknown')
    expect(meta.label).toBe('unknown')
  })
})

describe('PLATFORM_OPTIONS', () => {
  it('contains common platforms', () => {
    const values = PLATFORM_OPTIONS.map(p => p.value)
    expect(values).toContain('douyin')
    expect(values.length).toBeGreaterThan(3)
  })

  it('getPlatformName returns label for valid', () => {
    expect(getPlatformName('douyin')).toBeTruthy()
  })

  it('getPlatformName returns value for unknown', () => {
    expect(getPlatformName('unknown')).toBe('unknown')
  })

  it('getPlatformIcon returns icon for valid', () => {
    expect(getPlatformIcon('douyin')).toBeTruthy()
  })

  it('getPlatformIcon returns default for unknown', () => {
    expect(getPlatformIcon('unknown')).toBe('🌐')
  })
})

describe('TAG_PRESETS', () => {
  it('has items', () => {
    expect(TAG_PRESETS.length).toBeGreaterThan(0)
  })
})

describe('formatDate', () => {
  it('formats ISO date', () => {
    const result = formatDate('2024-01-15T10:30:00')
    expect(result).toMatch(/2024/)
    expect(result).toMatch(/01/)
  })
})

describe('truncate', () => {
  it('short text unchanged', () => {
    expect(truncate('short', 10)).toBe('short')
  })

  it('long text truncated', () => {
    expect(truncate('this is a long text', 10)).toBe('this is a …')
  })

  it('exact length unchanged', () => {
    expect(truncate('0123456789', 10)).toBe('0123456789')
  })
})
