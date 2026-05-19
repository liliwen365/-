<template>
  <div>
    <el-card>
      <template #header>已安装插件</template>
      <el-table :data="pluginStore.plugins">
        <el-table-column prop="display_name" label="名称" width="150" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="category" label="分类" width="80" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="$router.push(`/plugin/${row.name}`)">进入</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { usePluginStore } from '@/stores/plugin'
const pluginStore = usePluginStore()
</script>
