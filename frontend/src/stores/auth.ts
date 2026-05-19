import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const activated = ref(false)
  const machineId = ref('')

  async function checkStatus() {
    try {
      const { data } = await authApi.getStatus()
      activated.value = data.activated
      machineId.value = data.machine_id
    } catch {
      activated.value = false
    }
  }

  async function activate(code: string) {
    const { data } = await authApi.activate(code)
    if (data.success) {
      activated.value = true
    }
    return data
  }

  return { activated, machineId, checkStatus, activate }
})
