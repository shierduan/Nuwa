import WebSocket from 'ws';

export interface NuwaAccount {
  accountId: string;
  enabled: boolean;
  websocketUrl: string;
}

export interface NuwaMessage {
  id: string;
  type: 'text';
  content: string;
  channel: string;
  timestamp: number;
  from: { id: string; name: string };
  to?: { id: string; name: string };
}

export interface MessageHandler {
  (message: NuwaMessage): Promise<void>;
}

export class NuwaChannel {
  private config: NuwaAccount;
  private ws: WebSocket | null = null;
  private messageHandler: MessageHandler | null = null;
  private reconnectInterval: number = 5000;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isConnected: boolean = false;

  constructor(config: NuwaAccount) {
    this.config = config;
  }

  async start(handler: MessageHandler): Promise<void> {
    this.messageHandler = handler;
    await this.connect();
  }

  private async connect(): Promise<void> {
    try {
      this.ws = new WebSocket(this.config.websocketUrl);

      this.ws.on('open', () => {
        console.log('[NuwaChannel] Connected to Nuwa AI WebSocket server');
        this.isConnected = true;
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      });

      this.ws.on('message', (data: WebSocket.Data) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleNuwaMessage(message);
        } catch (error) {
          console.error('[NuwaChannel] Failed to parse message:', error);
        }
      });

      this.ws.on('error', (error) => {
        console.error('[NuwaChannel] WebSocket error:', error);
        this.isConnected = false;
        this.scheduleReconnect();
      });

      this.ws.on('close', (code, reason) => {
        console.log(`[NuwaChannel] WebSocket closed: ${code} - ${reason.toString()}`);
        this.isConnected = false;
        this.scheduleReconnect();
      });
    } catch (error) {
      console.error('[NuwaChannel] Failed to connect:', error);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        console.log('[NuwaChannel] Attempting to reconnect...');
        this.connect();
      }, this.reconnectInterval);
    }
  }

  private handleNuwaMessage(message: any): void {
    if (!this.messageHandler) return;

    try {
      // 处理女娲系统发送的消息
      if (message.type === 'text' || message.type === 'stream_chunk') {
        const content = message.content || '';
        if (content) {
          this.messageHandler({ 
            type: 'text',
            content,
            channel: 'nuwa',
            timestamp: Date.now(),
            id: `nuwa-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            from: { id: 'nuwa-ai', name: '女娲AI' }
          });
        }
      } else if (message.type === 'active_message') {
        const content = message.content || '';
        if (content) {
          this.messageHandler({ 
            type: 'text',
            content,
            channel: 'nuwa',
            timestamp: Date.now(),
            id: `nuwa-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            from: { id: 'nuwa-ai', name: '女娲AI' }
          });
        }
      }
    } catch (error) {
      console.error('[NuwaChannel] Failed to handle message:', error);
    }
  }

  async send(message: NuwaMessage): Promise<void> {
    if (!this.ws || !this.isConnected) {
      throw new Error('Not connected to Nuwa AI server');
    }

    try {
      // 将OpenClaw消息转换为女娲系统需要的格式
      const nuwaMessage = {
        type: 'text',
        content: message.content
      };

      this.ws.send(JSON.stringify(nuwaMessage));
      console.log('[NuwaChannel] Message sent to Nuwa AI:', message.content.substring(0, 50) + '...');
    } catch (error) {
      console.error('[NuwaChannel] Failed to send message:', error);
      throw error;
    }
  }

  async stop(): Promise<void> {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnected = false;
    this.messageHandler = null;
    console.log('[NuwaChannel] Channel stopped');
  }

  getStatus(): string {
    return this.isConnected ? 'connected' : 'disconnected';
  }
}