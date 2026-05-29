<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>系统信息</template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="版本">{{ info.version }}</el-descriptions-item>
            <el-descriptions-item label="操作系统">{{ formatPlatform(info.platform) }}</el-descriptions-item>
            <el-descriptions-item label="数据存储位置">{{ info.data_dir }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>已安装插件</template>
          <el-statistic :value="pluginStore.plugins.length" />
          <div v-if="pluginStore.plugins.length" style="margin-top: 12px">
            <el-tag v-for="p in pluginStore.plugins" :key="p.name" style="margin: 2px" @click="$router.push(`/plugin/${p.name}`)">
              {{ p.display_name }}
            </el-tag>
          </div>
          <el-empty v-else description="暂无插件，前往插件管理页面安装" :image-size="40" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>授权状态</template>
          <el-result v-if="authStore.activated" icon="success" title="已授权" sub-title="所有功能可正常使用" />
          <el-result v-else icon="warning" title="未授权" sub-title="软件未激活，部分功能受限。点击下方按钮前往激活">
            <template #extra>
              <el-button type="primary" @click="$router.push('/settings')">前往激活</el-button>
            </template>
          </el-result>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务统计 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="总任务数" :value="stats.total_tasks" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="今日任务" :value="stats.today_tasks" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="成功率">
            <template #default>{{ stats.success_rate }}%</template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="失败任务" :value="stats.failed_count" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { systemApi } from '@/api'
import api from '@/api'
import { usePluginStore } from '@/stores/plugin'
import { useAuthStore } from '@/stores/auth'

const pluginStore = usePluginStore()
const authStore = useAuthStore()
const info = ref<any>({})
const stats = ref<any>({
  total_tasks: 0,
  today_tasks: 0,
  success_rate: 0,
  failed_count: 0,
})

function formatPlatform(p: string): string {
  if (!p) return ''
  if (p.includes('win') || p === 'win32') return 'Windows'
  if (p === 'darwin') return 'macOS'
  if (p.includes('linux')) return 'Linux'
  return p
}

onMounted(async () => {
  try {
    const { data } = await systemApi.getInfo()
    info.value = data
  } catch {
    // 系统信息加载失败不影响页面
  }

  try {
    const { data: s } = await api.get('/api/system/stats')
    stats.value = s
  } catch {
    // 统计加载失败不影响页面
  }
})
</script>
