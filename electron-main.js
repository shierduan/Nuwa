// Electron主进程
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const url = require('url');

// 保持对窗口对象的全局引用，防止JavaScript对象被垃圾回收时窗口被自动关闭
let mainWindow;

function createWindow() {
    // 创建浏览器窗口
    mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        frame: false, // 无边框窗口，适合透明效果
        transparent: true, // 透明背景
        hasShadow: true, // 显示阴影
        alwaysOnTop: true, // 窗口置顶
        skipTaskbar: false, // 在任务栏显示
        resizable: true,
        webPreferences: {
            nodeIntegration: true, // 启用Node.js集成
            contextIsolation: false, // 关闭上下文隔离
            enableRemoteModule: true, // 启用远程模块
            devTools: true // 开发模式下启用DevTools
        }
    });
    
    // 强制默认不启用鼠标穿透，确保默认是解锁状态
    mainWindow.setIgnoreMouseEvents(false);
    console.log('Electron window default set to mouse not through');
    
    // 立即再次确认设置，防止被覆盖
    setTimeout(() => {
        mainWindow.setIgnoreMouseEvents(false);
        console.log('Electron window again confirm set to mouse not through');
    }, 100);
    
    // 移除可能导致窗口关闭的事件监听
    // mainWindow.on('close', (event) => {
    //     console.log('Electron窗口关闭事件被阻止，应用将继续运行');
    //     event.preventDefault();
    // });

    // 加载应用的index.html
    mainWindow.loadURL(url.format({
        pathname: path.join(__dirname, 'index.html'),
        protocol: 'file:',
        slashes: true
    }));

    // 打开DevTools（开发模式下）
    // mainWindow.webContents.openDevTools();

    // 窗口关闭时触发
    mainWindow.on('closed', () => {
        // 取消引用窗口对象，如果应用支持多窗口，通常会将窗口存储在数组中
        // 此时应该删除相应的元素
        mainWindow = null;
    });

    // 窗口隐藏时触发
    mainWindow.on('hide', () => {
        // 可以在这里添加隐藏时的逻辑
    });

    // 允许窗口拖拽
    mainWindow.webContents.on('did-finish-load', () => {
        // 告诉渲染进程窗口已经准备好
        mainWindow.webContents.send('window-ready');
    });
    
    // 创建托盘图标
    createTray();
}

// Electron初始化完成后创建窗口
app.on('ready', createWindow);

// 所有窗口关闭时退出应用
app.on('window-all-closed', () => {
    // 在macOS上，除非用户使用Cmd + Q明确退出，否则应用及其菜单栏会保持活动状态
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    // 在macOS上，当点击dock图标且没有其他窗口打开时，通常会重新创建一个窗口
    if (mainWindow === null) {
        createWindow();
    }
});

// 托盘图标支持
const { Tray, Menu } = require('electron');
let tray = null;

// 创建托盘图标
function createTray() {
    // 使用内置的托盘图标
    const trayIcon = 'https://cdn.jsdelivr.net/gh/electron/electron-api-demos@master/assets/win/Icon.png';
    
    tray = new Tray(trayIcon);
    
    // 创建托盘上下文菜单
    const contextMenu = Menu.buildFromTemplate([
        {
            label: '显示/隐藏',
            click: () => {
                if (mainWindow.isVisible()) {
                    mainWindow.hide();
                } else {
                    mainWindow.show();
                }
            }
        },
        {
            label: '切换置顶',
            type: 'checkbox',
            checked: mainWindow.isAlwaysOnTop(),
            click: (menuItem) => {
                mainWindow.setAlwaysOnTop(menuItem.checked);
            }
        },
        {
                label: '切换鼠标穿透',
                type: 'checkbox',
                checked: false, // 初始状态为未选中，与默认设置一致
                click: (menuItem) => {
                    mainWindow.setIgnoreMouseEvents(menuItem.checked, { forward: true });
                }
            },
        { type: 'separator' },
        {
            label: '开发者工具',
            click: () => {
                mainWindow.webContents.openDevTools();
            }
        },
        { type: 'separator' },
        {
            label: '退出',
            click: () => {
                app.quit();
            }
        }
    ]);
    
    // 设置托盘提示
    tray.setToolTip('Nuwa - 数字生命');
    
    // 设置托盘菜单
    tray.setContextMenu(contextMenu);
    
    // 点击托盘图标显示/隐藏窗口
    tray.on('click', () => {
        if (mainWindow.isVisible()) {
            mainWindow.hide();
        } else {
            mainWindow.show();
        }
    });
}

// IPC通信示例
ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
    mainWindow.setIgnoreMouseEvents(ignore, options);
});

// 全局鼠标追踪
const { screen } = require('electron');
let globalMouseTrackingInterval = null;

ipcMain.on('start-global-mouse-tracking', () => {
    if (globalMouseTrackingInterval) {
        clearInterval(globalMouseTrackingInterval);
    }
    
    // 每16ms（约60fps）获取一次全局鼠标位置
    globalMouseTrackingInterval = setInterval(() => {
        if (mainWindow && !mainWindow.isDestroyed()) {
            const point = screen.getCursorScreenPoint();
            const bounds = mainWindow.getBounds();
            
            // 计算鼠标相对于窗口的位置
            const relativeX = point.x - bounds.x;
            const relativeY = point.y - bounds.y;
            
            // 发送到渲染进程
            mainWindow.webContents.send('global-mouse-move', {
                screenX: point.x,
                screenY: point.y,
                clientX: relativeX,
                clientY: relativeY
            });
        }
    }, 16);
    
    console.log('全局鼠标追踪已启动');
});

ipcMain.on('stop-global-mouse-tracking', () => {
    if (globalMouseTrackingInterval) {
        clearInterval(globalMouseTrackingInterval);
        globalMouseTrackingInterval = null;
        console.log('全局鼠标追踪已停止');
    }
});

ipcMain.on('resize-window', (event, width, height) => {
    mainWindow.setSize(width, height);
});

ipcMain.on('move-window', (event, x, y) => {
    mainWindow.setPosition(x, y);
});

ipcMain.on('toggle-always-on-top', (event, alwaysOnTop) => {
    mainWindow.setAlwaysOnTop(alwaysOnTop);
});

ipcMain.on('toggle-dev-tools', (event) => {
    mainWindow.webContents.toggleDevTools();
});
