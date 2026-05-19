<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>系统信息</template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="版本">{{ info.version }}</el-descriptions-item>
            <el-descriptions-item label="平台">{{ info.platform }}</el-descriptions-item>
            <el-descriptions-item label="数据目录">{{ info.data_dir }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>已安装插件</template>
          <el-statistic :value="pluginStore.plugins.length" />
          <div style="margin-top: 12px">
            <el-tag v-for="p in pluginStore.plugins" :key="p.name" style="margin: 2px" @click="$router.push(`/plugin/${p.name}`)">
              {{ p.display_name }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>授权状态</template>
          <el-result v-if="authStore.activated" icon="success" title="已授权" sub-title="软件已激活" />
          <el-result v-else icon="warning" title="未授权" sub-title="请前往设置页面激活">
            <template #extra>
              <el-button type="primary" @click="$router.push('/settings')">去激活</el-button>
            </template>
          </el-result>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { systemApi } from '@/api'
import { usePluginStore } from '@/stores/plugin'
import { useAuthStore } from '@/stores/auth'

const pluginStore = usePluginStore()
const authStore = useAuthStore()
const info = ref<any>({})

onMounted(async () => {
  const { data } = await systemApi.getInfo()
  info.value = data
})
</script>
