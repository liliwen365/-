import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import api from '@/api'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const staticRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/index.vue'), meta: { title: '仪表板', icon: 'Monitor' } },
      { path: 'plugin-manage', name: 'PluginManage', component: () => import('@/views/plugin-manage/index.vue'), meta: { title: '插件管理', icon: 'Grid' } },
      { path: 'schedules', name: 'Schedules', component: () => import('@/views/schedules/index.vue'), meta: { title: '定时调度', icon: 'Timer' } },
      { path: 'settings', name: 'Settings', component: () => import('@/views/settings/index.vue'), meta: { title: '设置', icon: 'Setting' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: staticRoutes,
})

let dynamicRoutesLoaded = false

export async function setupDynamicRoutes() {
  try {
    const { data } = await api.get('/api/plugins/installed')
    for (const plugin of data.plugins || []) {
      const route: RouteRecordRaw = {
        path: `/plugin/${plugin.name}`,
        component: MainLayout,
        children: [
          {
            path: '',
            name: `Plugin_${plugin.name}`,
            component: () => import('@/views/plugin/PluginPage.vue'),
            meta: { title: plugin.display_name, icon: 'FolderOpened', plugin },
          },
        ],
      }
      router.addRoute(route)
    }
    dynamicRoutesLoaded = true
  } catch (e) {
    console.warn('加载动态路由失败:', e)
    dynamicRoutesLoaded = true
    ElMessage.error('插件加载失败，请刷新页面重试')
  }
}

// 导航守卫
router.beforeEach(async (to, from, next) => {
  // 首次加载：初始化授权状态和动态路由
  if (!dynamicRoutesLoaded) {
    const authStore = useAuthStore()
    await authStore.checkStatus()
    await setupDynamicRoutes()
    if (to.path.startsWith('/plugin/')) {
      next({ ...to, replace: true })
      return
    }
  }
  // 未激活：只允许访问设置页（激活入口）
  const authStore = useAuthStore()
  if (!authStore.activated && to.path !== '/settings') {
    next('/settings')
    return
  }
  next()
})

export default router
