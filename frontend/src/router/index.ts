import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const staticRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/index.vue'), meta: { title: '仪表板', icon: 'Monitor' } },
      { path: 'plugin-manage', name: 'PluginManage', component: () => import('@/views/plugin-manage/index.vue'), meta: { title: '插件管理', icon: 'Grid' } },
      { path: 'settings', name: 'Settings', component: () => import('@/views/settings/index.vue'), meta: { title: '设置', icon: 'Setting' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: staticRoutes,
})

// 动态路由注册：从后端获取已安装插件并注册路由
export async function setupDynamicRoutes() {
  try {
    const { default: axios } = await import('axios')
    const { data } = await axios.get('/api/plugins/installed')
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
  } catch (e) {
    console.warn('加载动态路由失败:', e)
  }
}

export default router
