import { defineStore } from 'pinia'
import { ref } from 'vue'
import { pluginApi } from '@/api'

export const usePluginStore = defineStore('plugin', () => {
  const plugins = ref<any[]>([])
  const loading = ref(false)

  async function fetchPlugins() {
    loading.value = true
    try {
      const { data } = await pluginApi.list()
      plugins.value = data.plugins || []
    } finally {
      loading.value = false
    }
  }

  return { plugins, loading, fetchPlugins }
})
