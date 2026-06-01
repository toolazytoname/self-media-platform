import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/content' },
    { path: '/content', name: 'Content', component: () => import('../views/Content/index.vue') },
    { path: '/content/create', name: 'ContentCreate', component: () => import('../views/Content/Create.vue') },
    { path: '/topic', name: 'Topic', component: () => import('../views/Topic/index.vue') },
    { path: '/material', name: 'Material', component: () => import('../views/Material/index.vue') },
    { path: '/review', name: 'Review', component: () => import('../views/Review/index.vue') },
    { path: '/platform', name: 'Platform', component: () => import('../views/Platform/index.vue') },
    { path: '/ai', name: 'AI', component: () => import('../views/AI/index.vue') },
    { path: '/stats', name: 'Stats', component: () => import('../views/Stats/index.vue') },
    { path: '/settings', name: 'Settings', component: () => import('../views/Settings/index.vue') }
  ]
})

export default router