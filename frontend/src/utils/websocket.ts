/**
 * 自动重连WebSocket。断线后指数退避重连，最多30秒间隔。
 */
export class ResilientWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectDelay = 30000
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private messageHandlers: Array<(data: any) => void> = []

  constructor(url: string) {
    this.url = url
  }

  connect() {
    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.messageHandlers.forEach(h => h(data))
      } catch {
        // 非JSON消息忽略
      }
    }

    this.ws.onclose = () => {
      const delay = Math.min(1000 * 2 ** this.reconnectAttempts, this.maxReconnectDelay)
      this.reconnectTimer = setTimeout(() => this.connect(), delay)
      this.reconnectAttempts++
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  onMessage(handler: (data: any) => void) {
    this.messageHandlers.push(handler)
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }
    this.ws?.close()
    this.ws = null
  }
}
