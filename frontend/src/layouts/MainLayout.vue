<template>
  <el-container class="main-layout">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <el-icon size="24"><Monitor /></el-icon>
        <span>本地自动化平台</span>
      </div>
      <el-menu :default-active="route.path" router class="sidebar-menu">
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>仪表板</span>
        </el-menu-item>

        <el-menu-item-group v-if="pluginStore.plugins.length">
          <template #title>插件</template>
          <el-menu-item
            v-for="p in pluginStore.plugins"
            :key="p.name"
            :index="`/plugin/${p.name}`"
          >
            <el-icon><FolderOpened /></el-icon>
            <span>{{ p.display_name }}</span>
          </el-menu-item>
        </el-menu-item-group>

        <el-menu-item index="/plugin-manage">
          <el-icon><Grid /></el-icon>
          <span>插件管理</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="page-title">{{ route.meta.title || '本地自动化平台' }}</span>
        <div class="header-right">
          <el-tag v-if="!authStore.activated" type="danger" size="small">未授权</el-tag>
          <el-tag v-else type="success" size="small">已授权</el-tag>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { usePluginStore } from '@/stores/plugin'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const pluginStore = usePluginStore()
const authStore = useAuthStore()

onMounted(async () => {
  await authStore.checkStatus()
  await pluginStore.fetchPlugins()
  // 动态路由由router.beforeEach守卫加载，此处不再调用setupDynamicRoutes
})
</script>

<style scoped>
.main-layout { height: 100vh; }
.sidebar { background: #001529; overflow-y: auto; }
.sidebar-menu { border-right: none; background: transparent; }
.sidebar-menu .el-menu-item { color: #ffffffa6; }
.sidebar-menu .el-menu-item:hover,
.sidebar-menu .el-menu-item.is-active { background: #ffffff1a; color: #fff; }
.sidebar-menu .el-menu-item-group__title { color: #ffffffa6; font-size: 12px; padding: 16px 0 4px 20px; }
.logo { height: 56px; display: flex; align-items: center; gap: 8px; padding: 0 20px; color: #fff; font-size: 16px; font-weight: 600; border-bottom: 1px solid #ffffff1a; }
.header { background: #fff; border-bottom: 1px solid #e8e8e8; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
.page-title { font-size: 16px; font-weight: 600; color: #333; }
.main-content { background: #f5f5f5; overflow-y: auto; }
</style>
