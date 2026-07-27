<template>
  <el-container class="main-layout">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <el-icon size="24"><Monitor /></el-icon>
        <div class="logo-text">
          <span>本地自动化平台</span>
          <span class="version-text" @click="copyVersion" title="点击复制版本号">
            v{{ sysInfo.version || '...' }}<template v-if="sysInfo.build_commit && sysInfo.build_commit !== 'dev'"> ({{ sysInfo.build_commit }})</template>
          </span>
        </div>
      </div>
      <el-menu :default-active="route.path" router class="sidebar-menu">
        <template v-if="authStore.activated">
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
          <el-menu-item index="/schedules">
            <el-icon><Timer /></el-icon>
            <span>定时调度</span>
          </el-menu-item>
        </template>
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
          <el-tag v-if="!authStore.activated" type="danger" size="small" style="cursor:pointer" @click="$router.push('/settings')">未授权 - 点击激活</el-tag>
          <el-tag v-else type="success" size="small">已授权</el-tag>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view :key="route.path" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { usePluginStore } from '@/stores/plugin'
import { useAuthStore } from '@/stores/auth'
import { systemApi } from '@/api'
import { ElMessage } from 'element-plus'
import { Timer } from '@element-plus/icons-vue'

const route = useRoute()
const pluginStore = usePluginStore()
const authStore = useAuthStore()
// 系统信息(版本/构建号)显示在侧边栏,报障时一眼对齐版本
const sysInfo = reactive<{ version?: string; build_commit?: string; build_time?: string }>({})

function copyVersion() {
  const v = `v${sysInfo.version || '?'} (${sysInfo.build_commit || '?'}, ${sysInfo.build_time || '?'})`
  try {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(v)
    } else {
      const ta = document.createElement('textarea')
      ta.value = v
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    ElMessage.success('版本号已复制')
  } catch {
    ElMessage.warning('复制失败,版本号见侧边栏')
  }
}

onMounted(async () => {
  await authStore.checkStatus()
  await pluginStore.fetchPlugins()
  try {
    const { data } = await systemApi.getInfo()
    Object.assign(sysInfo, data)
  } catch {
    // silent: 版本显示是辅助功能,失败不影响使用
  }
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
.logo-text { display: flex; flex-direction: column; line-height: 1.2; }
.version-text { font-size: 11px; font-weight: 400; color: #ffffff80; cursor: pointer; }
.version-text:hover { color: #fff; }
.header { background: #fff; border-bottom: 1px solid #e8e8e8; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
.page-title { font-size: 16px; font-weight: 600; color: #333; }
.main-content { background: #f5f5f5; overflow-y: auto; }
</style>
