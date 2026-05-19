import axios from 'axios'

const api = axios.create({ baseURL: '' })

export default api

export const systemApi = {
  getInfo: () => api.get('/api/system/info'),
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
  loadTemplate: (name: string, template: string) => api.get(`/api/plugins/${name}/templates/${encodeURIComponent(template)}`),
  getHistory: (name: string) => api.get(`/api/plugins/${name}/history`),
}
