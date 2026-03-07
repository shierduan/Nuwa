const builder = require('electron-builder');

builder.build({
  config: {
    appId: "com.nuwa.frontend",
    productName: "女娲",
    directories: {
      output: "dist"
    },
    files: [
      "index.html",
      "style.css",
      "main.js",
      "electron-main.js",
      "package.json",
      "启动管理器.html",
      "debug.html",
      "nuwa_main.py",
      "server_async.py",
      "manager.html"
    ],
    win: {
      target: "nsis"
    },
    nsis: {
      oneClick: false,
      allowToChangeInstallationDirectory: true
    }
  }
}).then(() => {
  console.log("✅ 编译完成！")
}).catch((error) => {
  console.error("❌ 编译失败:", error)
});