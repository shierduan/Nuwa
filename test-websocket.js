// 测试WebSocket消息处理逻辑
const WebSocket = require('ws');

// 创建WebSocket服务器
const wss = new WebSocket.Server({ port: 8080 });

console.log('WebSocket测试服务器已启动，端口8080');

wss.on('connection', (ws) => {
    console.log('客户端已连接');
    
    // 模拟后端发送生理监控数据
    const bioData = `[生理监控] 精力: 1.0000 | 混乱度: 0.3000 | 亲密度: 0.7000 
               驱动力 -> 社交饥渴: 0.6219 | 好奇心: 0.1420 
               情绪谱 -> 快乐:1.000 | 愤怒:0.000 | 悲伤:0.000 | 恐惧:0.000 | 信任:1.000 | 期待:1.000 
               情绪谱 -> 快乐:1.000 | 愤怒:0.000 | 悲伤:0.000 | 恐惧:0.000 | 信任:1.000 | 期待:1.000`;
    
    console.log('发送生理监控数据:', bioData);
    ws.send(bioData);
    
    // 5秒后关闭连接
    setTimeout(() => {
        console.log('关闭连接');
        ws.close();
    }, 5000);
});

wss.on('close', () => {
    console.log('服务器关闭');
});