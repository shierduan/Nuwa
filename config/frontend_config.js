
// 前端配置 - 请在浏览器控制台执行
localStorage.setItem('nuwaSettings', JSON.stringify({
  "backendUrl": "ws://127.0.0.1:8766",
  "modelScale": 1.0,
  "volume": 50,
  "debugMode": false,
  "currentModel": "local-model",
  "apiConfigs": [
    {
      "name": "桌面管理器配置",
      "wsUrl": "ws://127.0.0.1:8766",
      "llmUrl": "http://127.0.0.1:1234/v1",
      "apiKey": "lm-studio",
      "model": "local-model",
      "description": "由桌面管理器生成"
    }
  ],
  "currentApiConfig": 0
}));
console.log('配置已导入到浏览器localStorage');
