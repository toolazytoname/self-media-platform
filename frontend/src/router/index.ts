import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getToken } from '@/api/auth'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { hideLayout: true } },
  { path: '/', redirect: '/content' },
  { path: '/content', name: 'Content', component: () => import('../views/Content/index.vue') },
  { path: '/content/create', name: 'ContentCreate', component: () => import('../views/Content/Editor.vue') },
  { path: '/content/edit/:id', name: 'ContentEdit', component: () => import('../views/Content/Editor.vue') },
  { path: '/content/view/:id', name: 'ContentView', component: () => import('../views/Content/View.vue') },
  { path: '/topic', name: 'Topic', component: () => import('../views/Topic/index.vue') },
  { path: '/material', name: 'Material', component: () => import('../views/Material/index.vue') },
  { path: '/review', name: 'Review', component: () => import('../views/Review/index.vue') },
  { path: '/platform', name: 'Platform', component: () => import('../views/Platform/index.vue') },
  { path: '/publish-records', name: 'PublishRecords', component: () => import('../views/PublishRecords/index.vue') },
  { path: '/templates', name: 'Templates', component: () => import('../views/Templates/index.vue') },
  { path: '/ai', name: 'AI', component: () => import('../views/AI/index.vue') },
  { path: '/stats', name: 'Stats', component: () => import('../views/Stats/index.vue') },
  { path: '/settings', name: 'Settings', component: () => import('../views/Settings/index.vue') },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/NotFound.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 简单的路由守卫：未登录跳到 /login
router.beforeEach((to, _from, next) => {
  if (to.meta?.hideLayout) {
    return next()
  }
  if (!getToken()) {
    return next('/login')
  }
  next()
})

export default router

