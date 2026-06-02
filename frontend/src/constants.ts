// 共享常量
export const PLATFORMS: Record<string, { name: string; icon: string }> = {
  douyin: { name: '抖音', icon: '🎵' },
  bilibili: { name: 'B站', icon: '📺' },
  youtube: { name: 'YouTube', icon: '▶️' },
  xiaohongshu: { name: '小红书', icon: '📕' },
  toutiao: { name: '头条号', icon: '📰' },
  wechat: { name: '公众号', icon: '💬' },
  tiktok: { name: 'TikTok', icon: '🌍' },
  kuaishou: { name: '快手', icon: '⚡' },
  baijia: { name: '百家号', icon: '📚' },
  all: { name: '全部平台', icon: '🌐' },
}

export const PLATFORM_OPTIONS = Object.entries(PLATFORMS)
  .filter(([k]) => k !== 'all')
  .map(([key, v]) => ({ label: v.name, value: key }))

export const CONTENT_STATUSES = [
  { label: '草稿', value: 'draft', tagType: 'info' as const },
  { label: '待审核', value: 'pending', tagType: 'warning' as const },
  { label: '已发布', value: 'published', tagType: 'success' as const },
  { label: '失败', value: 'failed', tagType: 'danger' as const },
  { label: '已归档', value: 'archived', tagType: 'info' as const },
]

export const TAG_PRESETS = [
  { label: '科技', value: 'tech' },
  { label: '生活', value: 'life' },
  { label: '财经', value: 'finance' },
  { label: '娱乐', value: 'entertainment' },
  { label: '教育', value: 'education' },
  { label: '美食', value: 'food' },
  { label: '旅游', value: 'travel' },
  { label: '健康', value: 'health' },
  { label: '时尚', value: 'fashion' },
]

export const MATERIAL_TYPES = [
  { label: '全部', value: 'all' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
  { label: '音频', value: 'audio' },
  { label: '文本', value: 'text' },
]

export const TOPIC_STATUSES = [
  { label: '进行中', value: 'active' },
  { label: '已完成', value: 'done' },
  { label: '已归档', value: 'archived' },
]

export const REVIEW_STATUSES = [
  { label: '待审核', value: 'pending', tagType: 'warning' as const },
  { label: '已通过', value: 'approved', tagType: 'success' as const },
  { label: '已拒绝', value: 'rejected', tagType: 'danger' as const },
]

export const PUBLISH_STATUSES = [
  { label: '待处理', value: 'pending', tagType: 'warning' as const },
  { label: '已排期', value: 'scheduled', tagType: 'info' as const },
  { label: '已发布', value: 'published', tagType: 'success' as const },
  { label: '失败', value: 'failed', tagType: 'danger' as const },
]

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function formatDateShort(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return `${d.getMonth() + 1}/${d.getDate()}`
}

export function getStatusMeta(list: { value: string; tagType?: string; label: string }[], value: string) {
  return list.find(s => s.value === value) || { value, label: value, tagType: 'info' as const }
}

export function getPlatformName(key: string): string {
  return PLATFORMS[key]?.name || key
}

export function getPlatformIcon(key: string): string {
  return PLATFORMS[key]?.icon || '🌐'
}

export function truncate(text: string, max: number): string {
  if (!text) return ''
  if (text.length <= max) return text
  return text.slice(0, max) + '…'
}
