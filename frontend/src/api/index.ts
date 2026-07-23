import axios from 'axios'

const api = axios.create({ baseURL: '' })

let tokenPromise: Promise<string | null> | null = null

async function ensureToken(): Promise<string | null> {
  let token = localStorage.getItem('api_token')
  if (token) return token
  if (tokenPromise) return tokenPromise
  tokenPromise = axios.get('/api/system/token')
    .then(({ data }) => {
      const t = data.token
      if (t) localStorage.setItem('api_token', t)
      tokenPromise = null
      return t
    })
    .catch(() => {
      tokenPromise = null
      return null
    })
  return tokenPromise
}

api.interceptors.request.use(async (config) => {
  const token = await ensureToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401时重新获取token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('api_token')
      const token = await ensureToken()
      if (token) {
        error.config.headers.Authorization = `Bearer ${token}`
        return api.request(error.config)
      }
    }
    return Promise.reject(error)
  }
)

export default api

export const systemApi = {
  getInfo: () => api.get('/api/system/info'),
  openFolder: (path: string) => api.post('/api/system/open-folder', { path }),
}

export const authApi = {
  getStatus: () => api.get('/api/auth/status'),
  activate: (license_code: string) => api.post('/api/auth/activate', { license_code }),
  getMachineId: () => api.get('/api/auth/machine-id'),
}

export const pluginApi = {
  list: () => api.get('/api/plugins/installed'),
  getInfo: (name: string) => api.get(`/api/plugins/${name}/info`),
  getConfig: (name: string) => api.get(`/api/plugins/${name}/config`),
  saveConfig: (name: string, config: any) => api.put(`/api/plugins/${name}/config`, { config }),
  execute: (name: string, params: any, feature_id = '') => api.post(`/api/plugins/${name}/execute`, { params, feature_id }),
  getStatus: (name: string, taskId: number) => api.get(`/api/plugins/${name}/status`, { params: { task_id: taskId } }),
  cancel: (name: string, taskId: number) => api.post(`/api/plugins/${name}/cancel`, null, { params: { task_id: taskId } }),
  loadTemplate: (name: string, template: string) => api.get(`/api/plugins/${name}/templates/${encodeURIComponent(template)}`),
  getHistory: (name: string) => api.get(`/api/plugins/${name}/history`),
}
