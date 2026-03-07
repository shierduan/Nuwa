import { NuwaChannel, NuwaMessage } from './nuwa-channel';

async function testNuwaChannel() {
  console.log('Testing NuwaChannel connection...');

  const channel = new NuwaChannel({
    accountId: 'test',
    enabled: true,
    websocketUrl: 'ws://127.0.0.1:8766'
  });

  try {
    await channel.start(async (message: NuwaMessage) => {
      console.log('Received message from Nuwa AI:', message.content);
    });

    console.log('NuwaChannel started successfully');

    // Test sending a message
    await channel.send({
      id: 'test-123',
      type: 'text',
      content: '你好，女娲！我是OpenClaw聊天渠道。',
      channel: 'nuwa',
      timestamp: Date.now(),
      from: { id: 'test-user', name: 'Test User' },
      to: { id: 'nuwa-ai', name: 'Nuwa AI' }
    });

    console.log('Test message sent');

    // Keep connection open for 30 seconds
    setTimeout(async () => {
      console.log('Stopping NuwaChannel...');
      await channel.stop();
      console.log('NuwaChannel stopped');
    }, 30000);

  } catch (error) {
    console.error('Error testing NuwaChannel:', error);
    await channel.stop();
  }
}

// Run the test if this file is executed directly
if (require.main === module) {
  testNuwaChannel();
}