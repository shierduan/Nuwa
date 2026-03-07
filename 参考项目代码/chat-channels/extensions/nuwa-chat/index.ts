import { NuwaChannel, NuwaAccount } from './src/nuwa-channel';

export interface ChannelPlugin {
  id: string;
  name: string;
  description: string;
  meta?: any;
  onboarding?: any;
  pairing?: any;
  capabilities?: any;
  streaming?: any;
  reload?: any;
  configSchema?: any;
  config?: any;
  security?: any;
  groups?: any;
  mentions?: any;
  threading?: any;
  agentPrompt?: any;
  messaging?: any;
  directory?: any;
  resolver?: any;
  setup?: any;
  outbound?: any;
  status?: any;
  gateway?: any;
}

const plugin: ChannelPlugin = {
  id: 'nuwa-chat',
  name: 'Nuwa AI Chat',
  description: 'Integrates with Nuwa AI system for conversational AI capabilities',
  
  capabilities: {
    chatTypes: ['direct'],
    polls: false,
    reactions: false,
    threads: false,
    media: false,
    nativeCommands: false,
  },
  
  config: {
    listAccountIds: (cfg: any) => {
      if (cfg.channels?.nuwa?.accounts) {
        return Object.keys(cfg.channels.nuwa.accounts);
      }
      return ['default'];
    },
    resolveAccount: (cfg: any, accountId: string) => {
      const defaultConfig = {
        accountId: 'default',
        enabled: true,
        websocketUrl: 'ws://127.0.0.1:8766'
      };
      
      if (cfg.channels?.nuwa) {
        if (accountId === 'default' && !cfg.channels.nuwa.accounts) {
          return {
            ...defaultConfig,
            ...cfg.channels.nuwa
          };
        }
        if (cfg.channels.nuwa.accounts?.[accountId]) {
          return {
            ...defaultConfig,
            ...cfg.channels.nuwa.accounts[accountId],
            accountId
          };
        }
      }
      return defaultConfig;
    },
    defaultAccountId: (cfg: any) => 'default',
    isConfigured: (account: NuwaAccount) => Boolean(account.websocketUrl),
    describeAccount: (account: NuwaAccount) => ({
      accountId: account.accountId,
      name: account.accountId,
      enabled: account.enabled,
      configured: Boolean(account.websocketUrl),
    }),
  },
  
  outbound: {
    deliveryMode: 'direct',
    textChunkLimit: 2000,
    sendText: async ({ to, text, account }: any) => {
      const channel = new NuwaChannel(account);
      await channel.start(async () => {});
      
      try {
        await channel.send({
          id: `msg-${Date.now()}`,
          type: 'text',
          content: text,
          channel: 'nuwa',
          timestamp: Date.now(),
          from: { id: 'openclaw', name: 'OpenClaw' },
          to
        });
        
        return {
          channel: 'nuwa',
          messageId: `nuwa-${Date.now()}`,
          success: true
        };
      } finally {
        await channel.stop();
      }
    },
  },
};

export default plugin;