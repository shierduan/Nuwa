// 简单的WebSocket客户端测试脚本
console.log('===== WebSocket客户端测试开始 =====');
console.log('尝试连接到后端WebSocket服务...');

// 后端WebSocket地址
const backendUrl = 'ws://localhost:8000/ws';

// 创建WebSocket客户端
const ws = new WebSocket(backendUrl);

// 连接成功事件
ws.onopen = () => {
    console.log('✅ WebSocket连接成功！');
    console.log('连接地址:', backendUrl);
    
    // 发送测试消息
    const testMessage = { type: 'text', content: '你好' };
    console.log('发送消息:', testMessage);
    ws.send(JSON.stringify(testMessage));
    console.log('消息已发送');
};

// 收到消息事件
ws.onmessage = (event) => {
    console.log('✅ 收到后端响应:');
    console.log(event.data);
};

// 连接关闭事件
ws.onclose = (event) => {
    console.log('❌ WebSocket连接关闭！');
    console.log('关闭原因:', event.code, event.reason);
};

// 连接错误事件
ws.onerror = (error) => {
    console.log('❌ WebSocket连接错误！');
    console.log('错误信息:', error.message);
};

// 10秒后自动关闭连接
setTimeout(() => {
    console.log('⏱️  测试超时，关闭连接');
    ws.close();
}, 10000);
