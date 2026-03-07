// Nuwa-Frontend 核心逻辑
class NuwaFrontend {
    constructor() {
        this.app = null;
        this.model = null;
        this.websocket = null;
        this.reconnectTimer = null; // WebSocket重连定时器
        this.settings = {
            backendUrl: 'ws://127.0.0.1:8766',
            modelScale: 1.0,
            volume: 50,
            debugMode: false,
            currentModel: 'openSource',  // 当前选择的模型
            apiConfigs: [],  // API配置数组
            currentApiConfig: null,  // 当前使用的API配置索引
            ttsEnabled: false,  // TTS开关
            ttsModel: 'facebook/mms-tts-chinese',  // TTS模型
            live2dEnabled: false  // Live2D开关，默认关闭
        };
        this.isMenuOpen = false;
        this.mouseX = 0;
        this.mouseY = 0;
        this.isElectron = false;
        this.ipcRenderer = null;
        this.performanceData = {};
        this.expressionButtonsConfig = {}; // 存储每个模型的按钮配置 {modelName: [{name, file}, ...]}
        this.activeExpressionButtons = {}; // 存储每个按钮的激活状态 {buttonIndex: true/false}
        this.defaultExpressionParams = {}; // 保存默认表情参数，用于恢复 {paramId: value}
        this.buttonExpressionParams = {}; // 存储每个按钮应用的表达式参数 {buttonIndex: {paramId: value}}
        this.streamBuffer = ''; // 流式消息缓冲区，用于累积流式响应内容
        this.speechBubbleTimer = null; // 语音气泡自动隐藏定时器
        
        // 检测是否在Electron环境中
        this.detectElectron();
        
        // 等待DOM加载完成后初始化应用
        console.log('[Nuwa] 等待DOM加载完成...');
        window.addEventListener('load', () => {
            console.log('[Nuwa] DOM加载完成，开始初始化应用');
            this.init();
        });
    }
    
    // 检测是否在Electron环境中
    detectElectron() {
        if (typeof window !== 'undefined' && window.process && window.process.type) {
            this.isElectron = true;
            this.ipcRenderer = window.require('electron').ipcRenderer;
            this.log('Electron环境检测到');
            
            // 监听窗口准备就绪事件
            this.ipcRenderer.on('window-ready', () => {
                this.log('Electron窗口已准备就绪');
            });
        } else {
            this.isElectron = false;
            this.log('在浏览器环境中运行');
        }
    }
    
    // 初始化应用
    init() {
        // 首先加载保存的设置
        this.loadSettings();
        
        this.initCanvas();
        this.initSettingsMenu();
        this.initEventListeners();
        this.initChatInterface();
        this.initBioMonitor();
        this.initControlButtons();
        this.initExpressionButtons();
        this.initTTSControls(); // 添加TTS控制初始化
        this.initLive2DControls(); // 添加Live2D控制初始化
        this.bindMouseEvents(); // 确保Electron下可切换鼠标穿透，聊天按钮可点击
        
        // 添加全局错误处理
        window.addEventListener('error', (event) => {
            console.error('[Nuwa] 全局错误:', event.error);
            console.error('[Nuwa] 错误堆栈:', event.error.stack);
            this.showSpeechBubble(`应用错误: ${event.error.message}`);
        });
        
        // 加载Live2D模型（不依赖于WebSocket），但需要检查是否启用
        if (this.settings.live2dEnabled) {
            this.loadLive2DModel(this.settings.currentModel || 'openSource');
        }
        
        // 初始化WebSocket连接
        this.initWebSocket();
        
        // 启动连接状态监控
        setTimeout(() => {
            this.startConnectionMonitor();
            // 延迟检查连接，给WebSocket初始化留出时间
            setTimeout(async () => {
                const connected = await this.checkConnectionStatus();
                if (!connected) {
                    this.showQuickConnectTip();
                }
            }, 2000);
        }, 5000);
    }
    
    // 初始化聊天界面
    initChatInterface() {
        this.chatTrigger = document.getElementById('chat-trigger');
        this.floatingInput = document.getElementById('floating-input');
        this.messageInput = document.getElementById('message-input');
        
        // 确保聊天按钮可点击，添加事件监听器确保鼠标穿透被禁用
        if (this.isElectron) {
            this.chatTrigger.addEventListener('mouseenter', () => {
                this.ipcRenderer.send('set-ignore-mouse-events', false);
            });
        }
        
        // 绑定Chat Trigger按钮事件
        this.chatTrigger.addEventListener('click', (event) => {
            event.stopPropagation();
            this.log('聊天按钮被点击');
            
            // 立即禁用鼠标穿透，确保按钮点击有效
            if (this.isElectron) {
                this.ipcRenderer.send('set-ignore-mouse-events', false);
            }
            
            this.toggleFloatingInput();
        });
        
        // 绑定消息输入框事件
        this.messageInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        // 点击页面其他地方隐藏输入框
        document.addEventListener('click', (event) => {
            if (this.floatingInput.classList.contains('show') && 
                !this.floatingInput.contains(event.target) && 
                event.target !== this.chatTrigger) {
                this.hideFloatingInput();
            }
        });
        
        
    }
    
    // 绑定鼠标事件，用于切换鼠标穿透（仅在锁定状态下启用穿透）
    bindMouseEvents() {
        if (!this.isElectron) return;
        
        // 确保启动时默认不穿透
        this.ipcRenderer.send('set-ignore-mouse-events', false);
        this.log('启动时确保鼠标穿透已关闭');
        
        const canvasContainer = document.getElementById('canvas-container');
        const uiContainer = document.getElementById('chat-trigger');
        const controlButtons = document.querySelector('.control-buttons');
        
        // 定义鼠标事件处理函数
        const enableMouseCapture = () => {
            if (this.isElectron) {
                // 无论锁定状态如何，进入可交互区域都关闭穿透
                this.ipcRenderer.send('set-ignore-mouse-events', false);
            }
        };
        
        const enableMousePassthrough = () => {
            if (this.isElectron) {
                // 只有在锁定状态下才启用穿透
                const isLocked = this.lockBtn && this.lockBtn.classList.contains('locked');
                if (isLocked) {
                    this.ipcRenderer.send('set-ignore-mouse-events', true, { forward: true });
                } else {
                    // 未锁定状态，保持不穿透
                    this.ipcRenderer.send('set-ignore-mouse-events', false);
                }
            }
        };
        
        // 给Canvas容器添加鼠标事件（Live2D模型区域）
        if (canvasContainer) {
            canvasContainer.addEventListener('mouseenter', enableMouseCapture);
            canvasContainer.addEventListener('mouseleave', enableMousePassthrough);
        }
        
        // 给UI容器添加鼠标事件（Chat Trigger按钮）
        if (uiContainer) {
            uiContainer.addEventListener('mouseenter', enableMouseCapture);
            uiContainer.addEventListener('mouseleave', enableMousePassthrough);
        }
        if (controlButtons) {
            controlButtons.addEventListener('mouseenter', enableMouseCapture);
            controlButtons.addEventListener('mouseleave', enableMousePassthrough);
        }
        
        // 给浮动输入栏添加鼠标事件
        if (this.floatingInput) {
            this.floatingInput.addEventListener('mouseenter', enableMouseCapture);
            this.floatingInput.addEventListener('mouseleave', enableMousePassthrough);
        }
        
        // 给设置菜单添加鼠标事件
        const settingsMenu = document.getElementById('settings-menu');
        if (settingsMenu) {
            settingsMenu.addEventListener('mouseenter', enableMouseCapture);
            settingsMenu.addEventListener('mouseleave', enableMousePassthrough);
        }
        
        // 给生物监控HUD添加鼠标事件
        const bioMonitor = document.getElementById('bio-monitor');
        if (bioMonitor) {
            bioMonitor.addEventListener('mouseenter', enableMouseCapture);
            bioMonitor.addEventListener('mouseleave', enableMousePassthrough);
        }
    }
    
    // 初始化生理监控HUD
    initBioMonitor() {
        this.bioMonitor = document.getElementById('bio-monitor');
        this.energyBar = document.getElementById('energy-bar');
        this.energyValue = document.getElementById('energy-value');
        this.entropyBar = document.getElementById('entropy-bar');
        this.entropyValue = document.getElementById('entropy-value');
        this.hungerBar = document.getElementById('hunger-bar');
        this.hungerValue = document.getElementById('hunger-value');
        this.curiosityBar = document.getElementById('curiosity-bar');
        this.curiosityValue = document.getElementById('curiosity-value');
        this.intimacyBar = document.getElementById('intimacy-bar');
        this.intimacyValue = document.getElementById('intimacy-value');
        this.joyBar = document.getElementById('joy-bar');
        this.joyValue = document.getElementById('joy-value');
        this.angerBar = document.getElementById('anger-bar');
        this.angerValue = document.getElementById('anger-value');
        this.sadnessBar = document.getElementById('sadness-bar');
        this.sadnessValue = document.getElementById('sadness-value');
        this.fearBar = document.getElementById('fear-bar');
        this.fearValue = document.getElementById('fear-value');
        this.trustBar = document.getElementById('trust-bar');
        this.trustValue = document.getElementById('trust-value');
        this.expectationBar = document.getElementById('expectation-bar');
        this.expectationValue = document.getElementById('anticipation-value');
        this.disgustBar = document.getElementById('disgust-bar');
        this.disgustValue = document.getElementById('disgust-value');
        this.surpriseBar = document.getElementById('surprise-bar');
        this.surpriseValue = document.getElementById('surprise-value');
        
        // 初始值
        this.updateBioMonitor({ energy: 0.5, entropy: 0.2, social_hunger: 0.3, curiosity: 0.1, rapport: 0.7, joy: 1.0, anger: 0.0, sadness: 0.0, fear: 0.0, trust: 1.0, expectation: 1.0, disgust: 0.0, surprise: 0.0 });
    }
    
    // 切换浮动输入栏显示/隐藏
    toggleFloatingInput() {
        if (this.floatingInput.classList.contains('show')) {
            this.hideFloatingInput();
        } else {
            this.showFloatingInput();
        }
    }
    
    // 显示浮动输入栏
    showFloatingInput() {
        this.log('显示浮动输入栏');
        this.floatingInput.classList.add('show');
        
        // 确保鼠标穿透被禁用，允许点击输入框
        if (this.isElectron) {
            this.ipcRenderer.send('set-ignore-mouse-events', false);
        }
        
        // 延迟获取焦点，确保输入框已经完全显示
        setTimeout(() => {
            this.messageInput.focus();
            this.log('输入框获得焦点');
        }, 100);
    }
    
    // 隐藏浮动输入栏
    hideFloatingInput() {
        this.floatingInput.style.animation = 'fadeOutDown 0.3s ease';
        setTimeout(() => {
            this.floatingInput.classList.remove('show');
            this.floatingInput.style.animation = '';
            this.messageInput.value = '';
        }, 300);
    }
    
    // 发送消息
    sendMessage() {
        const message = this.messageInput.value.trim();
        this.log('===== 开始发送消息 =====');
        this.log('sendMessage called with message:', message);
        
        if (message) {
            this.log('准备发送消息:', message);
            
            // 清空流式缓冲区，准备接收新的流式响应
            this.streamBuffer = '';
            
            // 显示用户消息在聊天气泡中
            this.showSpeechBubble(`你说: ${message}`);
            
            // 立即显示思考中状态
            setTimeout(() => {
                 this.showSpeechBubble(`女娲: 思考中...`);
            }, 500);

            // 消息数据格式，确保与后端预期一致
            const messageData = {
                type: 'text',
                content: message,
                timestamp: new Date().toISOString()
            };
            
            this.log('准备发送的消息数据:', messageData);
            
            // 尝试通过WebSocket发送消息
            if (this.websocket) {
                this.log('WebSocket对象存在，状态:', this.websocket.readyState);
                
                if (this.websocket.readyState === WebSocket.OPEN) {
                    try {
                        const jsonMessage = JSON.stringify(messageData);
                        this.websocket.send(jsonMessage);
                        this.log('✅ 消息已通过WebSocket发送到后端');
                        this.log('发送的JSON数据:', jsonMessage);
                    } catch (sendError) {
                        this.log('❌ WebSocket消息发送失败:', sendError.message);
                        this.log('错误堆栈:', sendError.stack);
                    }
                } else {
                    this.log('⚠️ WebSocket未连接，状态:', this.websocket.readyState);
                    this.log('尝试重新初始化WebSocket...');
                    this.initWebSocket();
                    
                    // 延迟发送消息，等待连接建立
                    setTimeout(() => {
                        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                            this.websocket.send(JSON.stringify(messageData));
                            this.log('✅ 重新连接后发送消息成功');
                        } else {
                            this.log('❌ 重新连接失败');
                            this.showSpeechBubble(`连接失败: 无法连接到服务器`);
                        }
                    }, 1000);
                }
            } else {
                this.log('❌ WebSocket对象不存在，正在初始化...');
                this.initWebSocket();
                
                // 延迟发送消息，等待连接建立
                setTimeout(() => {
                    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                        this.websocket.send(JSON.stringify(messageData));
                        this.log('✅ 初始化后发送消息成功');
                    } else {
                        this.log('❌ 初始化失败');
                        this.showSpeechBubble(`连接失败: 无法连接到服务器`);
                    }
                }, 1000);
            }
            
            this.hideFloatingInput();
            this.log('===== 消息发送流程完成 =====');
        } else {
            this.log('⚠️ 消息为空，未发送');
        }
    }
    
    // 初始化Canvas（Pixi）
    initCanvas() {
        const container = document.getElementById('canvas-container');
        if (!container) {
            console.error('[Nuwa] ❌ 找不到 canvas-container');
            return;
        }
        
        // 确认Pixi可用
        if (typeof PIXI === 'undefined') {
            console.error('[Nuwa] ❌ 未加载 PIXI，请检查脚本引入');
            return;
        }
        
        // 清空旧内容
        container.innerHTML = '';
        
        // 创建Pixi应用
        this.app = new PIXI.Application({
            width: container.clientWidth || window.innerWidth,
            height: container.clientHeight || window.innerHeight,
            backgroundAlpha: 0,
            clearBeforeRender: true,
            transparent: true,
            antialias: true,
            resolution: window.devicePixelRatio || 1,
            autoDensity: true
        });
        
        // 允许交互
        this.app.stage.interactive = true;
        
        // 挂载画布
        container.appendChild(this.app.view);
        this.app.view.style.position = 'absolute';
        this.app.view.style.top = '0';
        this.app.view.style.left = '0';
        this.app.view.style.width = '100%';
        this.app.view.style.height = '100%';
        this.app.view.style.pointerEvents = 'auto';
        this.app.view.style.zIndex = '1';
        
        // 窗口变化时自适应
        window.addEventListener('resize', () => {
            const width = container.clientWidth || window.innerWidth;
            const height = container.clientHeight || window.innerHeight;
            this.app.renderer.resize(width, height);
            this.centerModel();
        });
        
        console.log('[Nuwa] Pixi Canvas 初始化完成');
    }
    
    // 加载Live2D模型（正式）
    loadLive2DModel(modelName = 'openSource') {
        console.log('[Nuwa] ===== 开始加载Live2D模型 =====');
        console.log('[Nuwa] 使用模型名称:', modelName);
        
        // 确认依赖
        const live2d = (typeof PIXI !== 'undefined' && PIXI.live2d) ? PIXI.live2d : null;
        if (!live2d || !live2d.Live2DModel || !live2d.Live2DModel.from) {
            console.error('[Nuwa] ❌ 未加载 PIXI 或 pixi-live2d-display，或 Live2DCubismCore 缺失');
            this.showSpeechBubble('Live2D依赖未就绪，请确认加载顺序: pixi → live2dcubismcore → pixi-live2d-display');
            return;
        }
        
        // 如果应用尚未初始化，先初始化
        if (!this.app) {
            this.initCanvas();
        }
        
        const modelUrl = `./models/${modelName}/${modelName}.model3.json`;
        const startTime = performance.now();
        
                // 清理旧模型和事件监听器
        if (this.model && this.app) {
            this.app.stage.removeChild(this.model);
            this.model = null;
        }
        
        // 重置表情状态
        this.activeExpressionButtons = {};
        this.defaultExpressionParams = {};
        this.buttonExpressionParams = {};
        
        // 重置所有按钮状态
        for (let i = 0; i < 8; i++) {
            this.updateExpressionButtonState(i, false);
        }
        
        // 清理旧的鼠标追踪事件监听器
        if (this.mouseTrackingHandlers && this.mouseTrackingHandlers.length > 0) {
            this.mouseTrackingHandlers.forEach(({ element, event, handler }) => {
                if (element === this.ipcRenderer) {
                    // IPC 事件使用 removeListener
                    element.removeListener(event, handler);
                } else {
                    // DOM 事件使用 removeEventListener
                    element.removeEventListener(event, handler);
                }
            });
            this.mouseTrackingHandlers = [];
        }
        
        // 停止全局鼠标追踪（如果正在运行）
        if (this.isElectron && this.ipcRenderer) {
            this.ipcRenderer.send('stop-global-mouse-tracking');
        }
        
        // 开始加载
        live2d.Live2DModel.from(modelUrl)
            .then((model) => {
                const loadTime = performance.now() - startTime;
                this.log(`模型加载成功，用时 ${loadTime.toFixed(2)}ms`);
                
                this.model = model;
                this.model.interactive = true;
                this.model.buttonMode = true;
                
                // 按设置缩放
                this.model.scale.set(this.settings.modelScale || 1.0);
                
                // 以底部居中为锚点（若支持 anchor）
                if (this.model.anchor && typeof this.model.anchor.set === 'function') {
                    this.model.anchor.set(0.5, 1);
                }
                
                // 放入舞台并居中
                this.app.stage.addChild(this.model);
                this.centerModel();
                
                // 交互与追踪
                this.enableMouseTracking(this.model);
                this.addModelInteractions(this.model);
                
                // 记录表达式信息
                if (this.model.internalModel && this.model.internalModel.motionManager) {
                    const expressionManager = this.model.internalModel.motionManager.expressionManager;
                    if (expressionManager) {
                        const definitions = expressionManager.definitions || [];
                        this.log(`模型加载了 ${definitions.length} 个表达式定义:`);
                        definitions.forEach((def, idx) => {
                            this.log(`  [${idx}] 文件: ${def.file || 'N/A'}, 名称: ${def.name || 'N/A'}`);
                        });
                    } else {
                        this.log(`⚠️ 表达式管理器不存在，模型可能没有定义表达式`);
                        this.log(`提示: 请检查模型的 .model3.json 文件中是否在 "FileReferences.Expressions" 中定义了表达式`);
                    }
                } else {
                    this.log(`⚠️ 模型内部管理器不存在`);
                }
                
                // 兼容旧代码：检查 model.expressions
                if (this.model.expressions) {
                    const expressionKeys = Object.keys(this.model.expressions);
                    this.log(`模型表达式对象键:`, expressionKeys);
                }
                
                // 性能记录
                this.startPerformanceTest(this.model, modelName, loadTime);
                
                // 更新表达式按钮配置
                this.updateExpressionButtonsForModel(modelName);
                
                this.showSpeechBubble(`Live2D模型 ${modelName} 加载成功！`);
                console.log('[Nuwa] ===== Live2D模型加载完成！=====');
            })
            .catch((error) => {
                console.error('[Nuwa] ❌ 模型加载异常:', error);
                this.showSpeechBubble(`模型加载异常: ${error.message}`);
            });
    }
    
    // 开始性能测试
    startPerformanceTest(model, modelName, loadTime) {
        this.log(`===== 开始 ${modelName} 模型性能测试 =====`);
        
        // 性能测试数据
        const performanceData = {
            modelName: modelName,
            loadTime: loadTime,
            frameTimes: [],
            fpsValues: [],
            startTime: performance.now()
        };
        
        // 记录当前模型的性能数据
        this.performanceData[modelName] = performanceData;
        
        // 每帧记录渲染时间
        let lastFrameTime = performance.now();
        const frameCounter = (timestamp) => {
            // 计算帧时间
            const currentFrameTime = performance.now();
            const frameTime = currentFrameTime - lastFrameTime;
            lastFrameTime = currentFrameTime;
            
            // 计算FPS
            const fps = frameTime > 0 ? 1000 / frameTime : 0;
            
            // 记录数据
            performanceData.frameTimes.push(frameTime);
            performanceData.fpsValues.push(fps);
            
            // 运行30秒后停止测试
            if (currentFrameTime - performanceData.startTime < 30000) {
                requestAnimationFrame(frameCounter);
            } else {
                // 结束测试，计算平均值
                this.endPerformanceTest(modelName);
            }
        };
        
        // 开始记录
        requestAnimationFrame(frameCounter);
        this.log(`✅ 性能测试已开始，将运行30秒`);
    }
    
    // 结束性能测试，计算结果
    endPerformanceTest(modelName) {
        const performanceData = this.performanceData[modelName];
        if (!performanceData) return;
        
        this.log(`===== ${modelName} 模型性能测试完成 =====`);
        
        // 计算平均帧时间
        const avgFrameTime = performanceData.frameTimes.reduce((sum, time) => sum + time, 0) / performanceData.frameTimes.length;
        
        // 计算平均FPS
        const avgFPS = performanceData.fpsValues.reduce((sum, fps) => sum + fps, 0) / performanceData.fpsValues.length;
        
        // 计算最大和最小FPS
        const maxFPS = Math.max(...performanceData.fpsValues);
        const minFPS = Math.min(...performanceData.fpsValues);
        
        // 记录结果
        performanceData.avgFrameTime = avgFrameTime;
        performanceData.avgFPS = avgFPS;
        performanceData.maxFPS = maxFPS;
        performanceData.minFPS = minFPS;
        
        // 输出结果
        this.log(`${modelName} 性能测试结果：`);
        this.log(`- 加载时间: ${performanceData.loadTime.toFixed(2)}ms`);
        this.log(`- 平均帧时间: ${avgFrameTime.toFixed(2)}ms`);
        this.log(`- 平均FPS: ${avgFPS.toFixed(2)}`);
        this.log(`- 最大FPS: ${maxFPS.toFixed(2)}`);
        this.log(`- 最小FPS: ${minFPS.toFixed(2)}`);
        this.log(`- 测试帧数: ${performanceData.frameTimes.length}`);
        
        // 显示在界面上
        this.showSpeechBubble(`${modelName} 性能测试完成！平均FPS: ${avgFPS.toFixed(0)}`);
        
        // 检查是否两个模型都已测试完成
        this.checkPerformanceTestComplete();
    }
    
    // 检查是否所有模型都已测试完成
    checkPerformanceTestComplete() {
        const hasOpenSource = this.performanceData && this.performanceData.openSource;
        const hasSideOpenSource = this.performanceData && this.performanceData.sideOpenSource;
        
        if (hasOpenSource && hasSideOpenSource) {
            this.compareModelsPerformance();
        }
    }
    
    // 比较两个模型的性能
    compareModelsPerformance() {
        const openSource = this.performanceData.openSource;
        const sideOpenSource = this.performanceData.sideOpenSource;
        
        this.log(`===== 模型性能比较结果 =====`);
        
        // 比较加载时间
        const loadTimeWinner = openSource.loadTime < sideOpenSource.loadTime ? 'openSource' : 'sideOpenSource';
        
        // 比较平均FPS
        const fpsWinner = openSource.avgFPS > sideOpenSource.avgFPS ? 'openSource' : 'sideOpenSource';
        
        // 比较平均帧时间
        const frameTimeWinner = openSource.avgFrameTime < sideOpenSource.avgFrameTime ? 'openSource' : 'sideOpenSource';
        
        // 输出比较结果
        this.log(`加载时间比较: openSource (${openSource.loadTime.toFixed(2)}ms) vs sideOpenSource (${sideOpenSource.loadTime.toFixed(2)}ms) - 胜者: ${loadTimeWinner}`);
        this.log(`平均FPS比较: openSource (${openSource.avgFPS.toFixed(2)}) vs sideOpenSource (${sideOpenSource.avgFPS.toFixed(2)}) - 胜者: ${fpsWinner}`);
        this.log(`平均帧时间比较: openSource (${openSource.avgFrameTime.toFixed(2)}ms) vs sideOpenSource (${sideOpenSource.avgFrameTime.toFixed(2)}ms) - 胜者: ${frameTimeWinner}`);
        
        // 综合判断哪个模型性能更好
        let overallWinner;
        const openSourceWins = [loadTimeWinner, fpsWinner, frameTimeWinner].filter(winner => winner === 'openSource').length;
        const sideOpenSourceWins = 3 - openSourceWins;
        
        if (openSourceWins > sideOpenSourceWins) {
            overallWinner = 'openSource';
        } else if (sideOpenSourceWins > openSourceWins) {
            overallWinner = 'sideOpenSource';
        } else {
            // 平局，比较平均FPS
            overallWinner = openSource.avgFPS > sideOpenSource.avgFPS ? 'openSource' : 'sideOpenSource';
        }
        
        this.log(`综合性能评估: ${overallWinner} 模型性能更好！`);
        this.showSpeechBubble(`模型性能比较完成！${overallWinner} 性能更好！`);
    }
    
    // 切换模型
    switchModel(modelName) {
        this.log(`===== 切换到 ${modelName} 模型 =====`);
        
        // 如果当前有模型，先移除
        if (this.model) {
            this.app.stage.removeChild(this.model);
            this.model = null;
        }
        
        // 重新加载新模型
        this.loadLive2DModel(modelName);
    }
    
    // 居中模型（基于窗口尺寸）
    centerModel() {
        if (!this.model || !this.app) return;
        
        // 获取窗口实际尺寸（容器或窗口）
        const container = document.getElementById('canvas-container');
        const windowWidth = container ? container.clientWidth : window.innerWidth;
        const windowHeight = container ? container.clientHeight : window.innerHeight;
        
        // 使用窗口尺寸而非屏幕尺寸
        const canvasWidth = windowWidth;
        const canvasHeight = windowHeight;
        
        if (this.model.anchor && typeof this.model.anchor.set === 'function') {
            // anchor 已设置 (0.5, 1)，直接定位窗口底部居中
            this.model.x = canvasWidth / 2;
            this.model.y = canvasHeight;
        } else {
            // 获取模型边界，手动计算居中/置底
            const bounds = this.model.getBounds();
            this.model.x = (canvasWidth - bounds.width * this.model.scale.x) / 2;
            this.model.y = canvasHeight - bounds.height * this.model.scale.y;
        }
    }
    
    // 启用鼠标追踪
    enableMouseTracking(model) {
        if (!model || !this.app) return;
        
        // 处理鼠标移动的通用函数
        const handleMouseMove = (clientX, clientY) => {
            if (!model || !this.app) return;
            
            this.mouseX = clientX || 0;
            this.mouseY = clientY || 0;
            
            // 获取鼠标在画布中的位置
            const canvasRect = this.app.view.getBoundingClientRect();
            const canvasX = this.mouseX - canvasRect.left;
            const canvasY = this.mouseY - canvasRect.top;
            
            // 转换为 Pixi 全局坐标
            let globalPoint;
            if (typeof PIXI !== 'undefined' && PIXI.Point) {
                globalPoint = new PIXI.Point(canvasX, canvasY);
            } else {
                globalPoint = { x: canvasX, y: canvasY };
            }
            
            // 转换为模型局部坐标
            let localPoint;
            try {
                if (typeof model.toLocal === 'function') {
                    localPoint = model.toLocal(globalPoint);
                } else {
                    throw new Error('toLocal not available');
                }
            } catch (e) {
                // 如果转换失败，使用屏幕坐标计算
                const bounds = model.getBounds();
                localPoint = {
                    x: canvasX - bounds.x,
                    y: canvasY - bounds.y
                };
            }
            
            // 获取模型尺寸（使用实际边界或默认值）
            const bounds = model.getBounds();
            const w = bounds.width || model.width || 1;
            const h = bounds.height || model.height || 1;
            
            // 归一化到 [-1, 1] 范围，以模型中心为原点
            const eyeX = Math.max(-1, Math.min(1, (localPoint.x / w - 0.5) * 2));
            const eyeY = Math.max(-1, Math.min(1, -(localPoint.y / h - 0.5) * 2)); // Y 轴反向
            
            // 更新眼睛参数
            if (model.internalModel) {
                try {
                    if (model.internalModel.coreModel && typeof model.internalModel.coreModel.setParameterValueById === 'function') {
                        // Cubism 4 API
                        model.internalModel.coreModel.setParameterValueById('ParamEyeBallX', eyeX);
                        model.internalModel.coreModel.setParameterValueById('ParamEyeBallY', eyeY);
                    } else if (typeof model.internalModel.setParamFloat === 'function') {
                        // Cubism 2 API
                        model.internalModel.setParamFloat('ParamEyeBallX', eyeX);
                        model.internalModel.setParamFloat('ParamEyeBallY', eyeY);
                    }
                } catch (e) {
                    // 参数设置失败时静默处理，避免影响其他功能
                    console.warn('[Nuwa] 眼睛追踪参数设置失败:', e);
                }
            }
            
            // 使用 Live2D 模型的 focus 方法实现头部追踪
            // focus 方法会自动处理头部角度计算，使用 focusController
            try {
                if (typeof model.focus === 'function') {
                    // focus 方法接受世界空间坐标（Pixi 坐标系统）
                    // 使用已经计算好的 globalPoint（Pixi 坐标）
                    model.focus(globalPoint.x, globalPoint.y, false);
                } else {
                    // 如果 focus 方法不可用，尝试直接设置头部参数
                    // 计算头部角度（使用更大的范围，通常头部转动范围更大）
                    const headAngleX = Math.max(-1, Math.min(1, (localPoint.x / w - 0.5) * 2)) * 0.5; // 头部左右转动，幅度较小
                    const headAngleY = Math.max(-1, Math.min(1, -(localPoint.y / h - 0.5) * 2)) * 0.3; // 头部上下转动，幅度更小
                    const headAngleZ = 0; // 头部倾斜
                    
                    if (model.internalModel) {
                        try {
                            if (model.internalModel.coreModel && typeof model.internalModel.coreModel.setParameterValueById === 'function') {
                                // Cubism 4 API
                                model.internalModel.coreModel.setParameterValueById('ParamAngleX', headAngleX);
                                model.internalModel.coreModel.setParameterValueById('ParamAngleY', headAngleY);
                                model.internalModel.coreModel.setParameterValueById('ParamAngleZ', headAngleZ);
                            } else if (typeof model.internalModel.setParamFloat === 'function') {
                                // Cubism 2 API
                                model.internalModel.setParamFloat('ParamAngleX', headAngleX);
                                model.internalModel.setParamFloat('ParamAngleY', headAngleY);
                                model.internalModel.setParamFloat('ParamAngleZ', headAngleZ);
                            }
                        } catch (e) {
                            // 如果头部参数不存在，静默忽略（某些模型可能没有这些参数）
                        }
                    }
                }
            } catch (e) {
                console.warn('[Nuwa] 头部追踪设置失败:', e);
            }
        };
        
        // 在 Electron 环境中，使用全局鼠标追踪
        if (this.isElectron && this.ipcRenderer) {
            // 监听来自主进程的全局鼠标位置
            const globalMouseHandler = (event, data) => {
                handleMouseMove(data.clientX, data.clientY);
            };
            
            this.ipcRenderer.on('global-mouse-move', globalMouseHandler);
            
            // 启动全局鼠标追踪
            this.ipcRenderer.send('start-global-mouse-tracking');
            
            // 保存事件处理器引用，以便后续清理
            if (!this.mouseTrackingHandlers) {
                this.mouseTrackingHandlers = [];
            }
            this.mouseTrackingHandlers.push({
                element: this.ipcRenderer,
                event: 'global-mouse-move',
                handler: globalMouseHandler
            });
            
            this.log('鼠标追踪已启用（使用全局屏幕追踪）');
        } else {
            // 在浏览器环境中，使用窗口内鼠标事件
            const handleMouseMoveEvent = (event) => {
                handleMouseMove(event.clientX || event.x || 0, event.clientY || event.y || 0);
            };
            
            document.addEventListener('mousemove', handleMouseMoveEvent);
            
            // 保存事件处理器引用，以便后续清理
            if (!this.mouseTrackingHandlers) {
                this.mouseTrackingHandlers = [];
            }
            this.mouseTrackingHandlers.push({
                element: document,
                event: 'mousemove',
                handler: handleMouseMoveEvent
            });
            
            this.log('鼠标追踪已启用（使用窗口内事件监听）');
        }
    }
    
    // 添加模型交互事件
    addModelInteractions(model) {
        // 双击事件 - 触发随机动作并发送Poke事件（兼容不同 pointer API）
        model.on('pointerdown', (event) => {
            const ev = event.data?.originalEvent || event.data;
            const pointerType = ev?.pointerType || ev?.type || 'mouse';
            if (pointerType === 'mouse' && ev?.button === 2) {
                ev.preventDefault?.();
            }
        });
        
        // 双击事件
        model.on('pointertap', (event) => {
            const ev = event.data?.originalEvent || event.data;
            const pointerType = ev?.pointerType || ev?.type || 'mouse';
            const clickCount = typeof event.data?.getClickCount === 'function' ? event.data.getClickCount() : (ev?.detail || 1);
            if (pointerType === 'mouse' && clickCount >= 2) {
                this.triggerRandomMotion();
                this.sendWebSocketMessage({ type: 'poke' });
            }
        });
        
        // 右键菜单事件
        model.on('rightclick', (event) => {
            const ev = event.data?.originalEvent || event.data;
            ev?.preventDefault?.();
            this.toggleSettingsMenu();
        });
    }
    
    // 触发随机动作
    triggerRandomMotion() {
        if (!this.model || !this.model.motions) return;
        
        // 获取所有可用动作
        const motionGroups = Object.keys(this.model.motions);
        if (motionGroups.length === 0) return;
        
        // 随机选择一个动作组
        const randomGroup = motionGroups[Math.floor(Math.random() * motionGroups.length)];
        const motions = this.model.motions[randomGroup];
        
        if (motions && motions.length > 0) {
            // 随机选择一个动作
            const randomMotion = motions[Math.floor(Math.random() * motions.length)];
            this.model.motion(randomGroup, randomMotion.index);
            this.log(`触发动作: ${randomGroup} - ${randomMotion.index}`);
        }
    }
    
    // 初始化WebSocket连接
    initWebSocket() {
        this.log('===== 开始初始化WebSocket连接 =====');
        this.log(`环境检测: Electron=${this.isElectron}, WebSocket支持=${typeof WebSocket !== 'undefined'}`);
        this.log(`连接URL: ${this.settings.backendUrl}`);
        
        try {
            // 检查WebSocket是否支持
            if (typeof WebSocket === 'undefined') {
                throw new Error('WebSocket is not supported in this environment');
            }
            
            this.websocket = new WebSocket(this.settings.backendUrl);
            this.log('WebSocket对象已创建');
            
            this.websocket.onopen = () => {
                this.log('✅ WebSocket连接成功！状态:', this.websocket.readyState);
                this.log('连接URL:', this.websocket.url);
                
                // 发送测试消息
                const testMessage = { type: 'test', content: '连接测试' };
                this.websocket.send(JSON.stringify(testMessage));
                this.log('已发送测试消息:', testMessage);
                
                // 发送TTS配置（如果已启用）
                if (this.settings.ttsEnabled) {
                    setTimeout(() => {
                        this.sendTTSConfig();
                        this.queryTTSStatus();
                    }, 500);
                }
                
                // 连接成功后清除重连定时器
                if (this.reconnectTimer) {
                    clearTimeout(this.reconnectTimer);
                    this.reconnectTimer = null;
                }
            };
            
            this.websocket.onmessage = (event) => {
                this.log('✅ 收到WebSocket消息:', event.data);
                try {
                    // 尝试解析为JSON格式
                    const data = JSON.parse(event.data);
                    this.log('解析后的消息:', data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    // 如果解析失败，将其作为纯文本处理
                    this.log('❌ 消息解析失败，作为纯文本处理:', event.data);
                    this.parseAndDisplayMessage(event.data);
                }
            };
            
            this.websocket.onclose = (event) => {
                this.log('❌ WebSocket连接关闭！');
                this.log('关闭原因:', event.code, event.reason);
                this.log('是否正常关闭:', event.wasClean);
                
                // 添加自动重连机制
                if (!this.reconnectTimer) {
                    this.log('⚠️  WebSocket连接已关闭，将在3秒后自动重连');
                    this.reconnectTimer = setTimeout(() => {
                        this.log('🔄 尝试重新连接WebSocket...');
                        this.initWebSocket();
                    }, 3000);
                }
            };
            
            this.websocket.onerror = (error) => {
                this.log('❌ WebSocket连接错误！');
                this.log('错误信息:', error.message || '未知错误');
            };
            
            this.log('WebSocket事件监听器已添加');
        } catch (error) {
            this.log('❌ WebSocket初始化失败:', error.message);
            this.log('错误堆栈:', error.stack);
            
            // 初始化失败时也添加自动重连
            if (!this.reconnectTimer) {
                this.log('⚠️  WebSocket初始化失败，将在3秒后自动重试');
                this.reconnectTimer = setTimeout(() => {
                    this.log('🔄 尝试重新初始化WebSocket...');
                    this.initWebSocket();
                }, 3000);
            }
        }
        this.log('===== WebSocket初始化完成 =====');
    }
    
    // 处理WebSocket消息
    handleWebSocketMessage(data) {
        this.log('收到消息:', data);
        
        // 无论调试模式如何，都记录状态更新消息，方便调试
        if (data.type === 'status_update') {
            this.log('✅ 收到状态更新消息，包含生理监控数据');
            this.log('   精力值:', data.energy);
            this.log('   混乱度:', data.system_entropy);
            this.log('   亲密度:', data.rapport);
            this.log('   社交饥渴:', data.drives?.social_hunger);
            this.log('   好奇心:', data.drives?.curiosity);
            this.log('   情绪谱:', data.emotional_spectrum);
            
            // 在调试模式下显示完整的生理监控数据
            if (this.settings.debugMode) {
                this.log('📊 完整生理监控数据:', JSON.stringify(data, null, 2));
            }
        }
        
        switch (data.type) {
            case 'text':
                this.parseAndDisplayMessage(data.content);
                break;
            case 'status_update':
                // 处理状态更新消息
                this.updateBioMonitor({
                    energy: data.energy || 0,
                    entropy: data.system_entropy || 0,
                    rapport: data.rapport || 0,
                    social_hunger: data.drives?.social_hunger || 0,
                    curiosity: data.drives?.curiosity || 0,
                    joy: data.emotional_spectrum?.joy || 0,
                    anger: data.emotional_spectrum?.anger || 0,
                    sadness: data.emotional_spectrum?.sadness || 0,
                    fear: data.emotional_spectrum?.fear || 0,
                    trust: data.emotional_spectrum?.trust || 0,
                    expectation: data.emotional_spectrum?.anticipation || 0,
                    disgust: data.emotional_spectrum?.disgust || 0,
                    surprise: data.emotional_spectrum?.surprise || 0
                });
                break;
            case 'active_message':
                // 处理主动消息
                this.log('处理主动消息:', data);
                this.showSpeechBubble(`女娲: ${data.content}`);
                break;
            case 'stream_chunk':
                // 处理流式消息块
                this.handleStreamChunk(data.content);
                break;
            case 'stream_end':
                // 流式传输结束
                this.handleStreamEnd();
                break;
            case 'motion':
                this.playMotion(data.motionGroup, data.motionIndex);
                break;
            case 'emotion':
                this.setEmotion(data.emotion);
                break;
            case 'volume':
                this.settings.volume = data.volume;
                this.updateVolumeSlider();
                break;
            case 'error':
                this.showSpeechBubble(`错误: ${data.content}`);
                this.streamBuffer = ''; // 清空缓冲区
                break;
            case 'audio':
                // 处理TTS音频数据
                this.handleTTSAudio(data.data, data.text);
                break;
            case 'tts_config_response':
                // 处理TTS配置响应
                if (data.status === 'success') {
                    this.showTTSFeedback(data.message, 'success');
                    this.updateTTSStatusDisplay();
                } else {
                    this.showTTSFeedback('TTS配置失败', 'error');
                }
                break;
            case 'tts_status_response':
                // 处理TTS状态响应
                if (data.status) {
                    this.log('TTS状态:', data.status);
                    // 可以在这里更新UI显示详细状态
                }
                break;
            default:
                this.log('未知消息类型:', data.type);
        }
    }
    
    // 处理流式消息块
    handleStreamChunk(chunk) {
        if (!chunk) return;
        
        // 累积到缓冲区
        this.streamBuffer += chunk;
        this.log('流式块:', chunk, '缓冲区长度:', this.streamBuffer.length);
        
        // 实时解析并显示 <speak> 标签内的内容
        this.updateStreamDisplay();
    }
    
    // 更新流式显示
    updateStreamDisplay() {
        // 查找所有完整的 <speak> 标签
        const speakMatches = this.streamBuffer.match(/<speak>(.*?)<\/speak>/gs);
        if (speakMatches && speakMatches.length > 0) {
            // 取最后一个完整的 <speak> 标签内容
            const lastMatch = speakMatches[speakMatches.length - 1];
            const speakContent = lastMatch.replace(/<\/?speak>/g, '').trim();
            if (speakContent) {
                this.showSpeechBubble(speakContent, false); // false表示不自动隐藏
            }
        } else {
            // 检查是否有未闭合的 <speak> 标签
            const openSpeakMatch = this.streamBuffer.match(/<speak>(.*)$/s);
            if (openSpeakMatch) {
                const partialContent = openSpeakMatch[1].trim();
                if (partialContent) {
                    this.showSpeechBubble(partialContent, false);
                }
            }
        }
    }
    
    // 处理流式传输结束
    handleStreamEnd() {
        this.log('流式传输结束，最终缓冲区:', this.streamBuffer);
        
        // 最终解析完整响应
        if (this.streamBuffer) {
            // 提取 <speak> 标签内的最终内容
            const speakMatches = this.streamBuffer.match(/<speak>(.*?)<\/speak>/gs);
            if (speakMatches && speakMatches.length > 0) {
                const finalContent = speakMatches[speakMatches.length - 1]
                    .replace(/<\/?speak>/g, '')
                    .trim();
                if (finalContent) {
                    this.showSpeechBubble(finalContent, true); // true表示正常显示（会自动隐藏）
                }
            } else {
                // 如果没有找到完整的 <speak> 标签，尝试提取未闭合的内容
                const openSpeakMatch = this.streamBuffer.match(/<speak>(.*)$/s);
                if (openSpeakMatch) {
                    const finalContent = openSpeakMatch[1].trim();
                    if (finalContent) {
                        this.showSpeechBubble(finalContent, true);
                    }
                }
            }
        }
        
        // 清空缓冲区
        this.streamBuffer = '';
    }
    
    // 解析并显示消息
    parseAndDisplayMessage(rawMessage) {
        this.log('原始消息:', rawMessage);
        
        // 解析生理监控数据
        this.parseBioMonitorData(rawMessage);
        
        // 解析回复文本
        const replyText = this.extractReplyText(rawMessage);
        if (replyText) {
            this.showSpeechBubble(replyText);
        }
    }
    
    // 解析生理监控数据
    parseBioMonitorData(rawMessage) {
        if (!rawMessage || typeof rawMessage !== 'string') {
            this.log('⚠️ 生理监控数据解析：消息为空或不是字符串');
            return;
        }
        
        this.log('开始解析生理监控数据，消息长度:', rawMessage.length);
        this.log('消息内容预览:', rawMessage.substring(0, 200));
        
        // 检查是否包含生理监控标记
        if (!rawMessage.includes('生理监控') && !rawMessage.includes('Energy') && !rawMessage.includes('Entropy')) {
            this.log('⚠️ 消息中未找到生理监控标记');
            return;
        }
        
        // 匹配新的生理监控数据格式，使用多行模式
        const bioRegex = /\[生理监控\][\s\S]*?精力: ([0-9.]+) \| 混乱度: ([0-9.]+) \| 亲密度: ([0-9.]+)/i;
        const bioMatch = rawMessage.match(bioRegex);
        
        if (bioMatch) {
            this.log('✅ 匹配到新格式生理监控数据');
            const energy = parseFloat(bioMatch[1]);
            const entropy = parseFloat(bioMatch[2]);
            const intimacy = parseFloat(bioMatch[3]);
            
            // 匹配驱动力数据，使用多行模式
            const driveRegex = /驱动力[\s\S]*?社交饥渴: ([0-9.]+)[\s\S]*?好奇心: ([0-9.]+)/i;
            const driveMatch = rawMessage.match(driveRegex);
            
            const social_hunger = driveMatch ? parseFloat(driveMatch[1]) : 0.0;
            const curiosity = driveMatch ? parseFloat(driveMatch[2]) : 0.0;
            
            // 匹配情绪谱数据，使用多行模式，更宽松的匹配，支持8种基本情绪
            const emotionRegex = /情绪谱[\s\S]*?快乐[:\s]*([0-9.]+)[\s\S]*?愤怒[:\s]*([0-9.]+)[\s\S]*?悲伤[:\s]*([0-9.]+)[\s\S]*?恐惧[:\s]*([0-9.]+)[\s\S]*?信任[:\s]*([0-9.]+)[\s\S]*?厌恶[:\s]*([0-9.]+)?[\s\S]*?期待[:\s]*([0-9.]+)[\s\S]*?惊讶[:\s]*([0-9.]+)?/i;
            const emotionMatch = rawMessage.match(emotionRegex);
            
            const joy = emotionMatch ? parseFloat(emotionMatch[1]) : 0.0;
            const anger = emotionMatch ? parseFloat(emotionMatch[2]) : 0.0;
            const sadness = emotionMatch ? parseFloat(emotionMatch[3]) : 0.0;
            const fear = emotionMatch ? parseFloat(emotionMatch[4]) : 0.0;
            const trust = emotionMatch ? parseFloat(emotionMatch[5]) : 0.0;
            const disgust = emotionMatch && emotionMatch[6] ? parseFloat(emotionMatch[6]) : 0.0;
            const expectation = emotionMatch ? parseFloat(emotionMatch[7]) : 0.0;
            const surprise = emotionMatch && emotionMatch[8] ? parseFloat(emotionMatch[8]) : 0.0;
            
            const bioData = {
                energy: energy,
                entropy: entropy,
                social_hunger: social_hunger,
                curiosity: curiosity,
                rapport: intimacy,
                joy: joy,
                anger: anger,
                sadness: sadness,
                fear: fear,
                trust: trust,
                expectation: expectation,
                disgust: disgust,
                surprise: surprise
            };
            
            this.log('✅ 解析到的生理监控数据:', bioData);
            this.updateBioMonitor(bioData);
            return;
        }
        
        // 保留旧格式兼容
        const oldBioRegex = /\[生理监控\].*?Energy: ([0-9.]+) \| Entropy: ([0-9.]+) \| Hunger: ([0-9.]+)/i;
        const oldBioMatch = rawMessage.match(oldBioRegex);
        
        if (oldBioMatch) {
            this.log('✅ 匹配到旧格式生理监控数据');
            const energy = parseFloat(oldBioMatch[1]);
            const entropy = parseFloat(oldBioMatch[2]);
            const hunger = parseFloat(oldBioMatch[3]);
            
            this.updateBioMonitor({
                energy: energy,
                entropy: entropy,
                social_hunger: hunger
            });
            return;
        }
        
        // 保留更详细的旧生理监控格式兼容
        const detailedBioRegex = /\[生理监控\].*?Energy: ([0-9.]+).*?Entropy: ([0-9.]+).*?Social Hunger: ([0-9.]+).*?Intimacy: ([0-9.]+)/i;
        const detailedBioMatch = rawMessage.match(detailedBioRegex);
        
        if (detailedBioMatch) {
            this.log('✅ 匹配到详细旧格式生理监控数据');
            const energy = parseFloat(detailedBioMatch[1]);
            const entropy = parseFloat(detailedBioMatch[2]);
            const hunger = parseFloat(detailedBioMatch[3]);
            const intimacy = parseFloat(detailedBioMatch[4]);
            
            this.updateBioMonitor({
                energy: energy,
                entropy: entropy,
                social_hunger: hunger,
                rapport: intimacy
            });
            return;
        }
        
        this.log('⚠️ 未能匹配任何生理监控数据格式');
    }
    
    // 提取回复文本
    extractReplyText(rawMessage) {
        // 移除思维内容
        let cleanedMessage = rawMessage;
        
        // 移除[思维]...内容
        cleanedMessage = cleanedMessage.replace(/\[思维\].*?(?=\[|$)/gs, '');
        
        // 移除<thought>...</thought>内容
        cleanedMessage = cleanedMessage.replace(/<thought>.*?<\/thought>/gs, '');
        
        // 提取[回复] 女娲: 后的文本
        const replyRegex = /\[回复\]\s*(?:女娲|Nuwa):\s*(.*?)(?=\[|$)/gs;
        const matches = [...cleanedMessage.matchAll(replyRegex)];
        
        if (matches.length > 0) {
            // 合并所有匹配到的回复文本
            return matches.map(match => match[1].trim()).join(' ');
        }
        
        // 提取直接回复文本（没有标签的情况）
        const directReplyRegex = /^(?!\[思维\]|\[生理监控\]|\[回复\])(.*?)$/gm;
        const directMatches = [...cleanedMessage.matchAll(directReplyRegex)];
        
        if (directMatches.length > 0) {
            return directMatches.map(match => match[1].trim()).join(' ');
        }
        
        return null;
    }
    
    // 更新生理监控HUD
    updateBioMonitor(data) {
        if (!data) {
            this.log('⚠️ updateBioMonitor: 数据为空');
            return;
        }
        
        // 检查元素是否存在
        if (!this.energyBar || !this.energyValue) {
            this.log('⚠️ 生理监控元素未初始化，尝试重新初始化...');
            this.initBioMonitor();
        }
        
        this.log('更新生理监控HUD，数据:', data);
        
        // 更新能量
        if (data.energy !== undefined && this.energyBar && this.energyValue) {
            const energyPercent = Math.max(0, Math.min(100, data.energy * 100));
            this.energyBar.style.width = `${energyPercent}%`;
            this.energyValue.textContent = data.energy.toFixed(1);
            this.log(`更新能量: ${data.energy} (${energyPercent}%)`);
        }
        
        // 更新熵值
        if (data.entropy !== undefined && this.entropyBar && this.entropyValue) {
            const entropyPercent = Math.max(0, Math.min(100, data.entropy * 100));
            this.entropyBar.style.width = `${entropyPercent}%`;
            this.entropyValue.textContent = data.entropy.toFixed(1);
        }
        
        // 更新社交饥渴
        if (data.social_hunger !== undefined && this.hungerBar && this.hungerValue) {
            const hungerPercent = Math.max(0, Math.min(100, data.social_hunger * 100));
            this.hungerBar.style.width = `${hungerPercent}%`;
            this.hungerValue.textContent = data.social_hunger.toFixed(1);
        }
        
        // 更新好奇心
        if (data.curiosity !== undefined && this.curiosityBar && this.curiosityValue) {
            const curiosityPercent = Math.max(0, Math.min(100, data.curiosity * 100));
            this.curiosityBar.style.width = `${curiosityPercent}%`;
            this.curiosityValue.textContent = data.curiosity.toFixed(1);
        }
        
        // 更新亲密度
        if (data.rapport !== undefined && this.intimacyBar && this.intimacyValue) {
            const intimacyPercent = Math.max(0, Math.min(100, data.rapport * 100));
            this.intimacyBar.style.width = `${intimacyPercent}%`;
            this.intimacyValue.textContent = data.rapport.toFixed(1);
        }
        
        // 更新快乐
        if (data.joy !== undefined && this.joyBar && this.joyValue) {
            const joyPercent = Math.max(0, Math.min(100, data.joy * 100));
            this.joyBar.style.width = `${joyPercent}%`;
            this.joyValue.textContent = data.joy.toFixed(1);
        }
        
        // 更新愤怒
        if (data.anger !== undefined && this.angerBar && this.angerValue) {
            const angerPercent = Math.max(0, Math.min(100, data.anger * 100));
            this.angerBar.style.width = `${angerPercent}%`;
            this.angerValue.textContent = data.anger.toFixed(1);
        }
        
        // 更新悲伤
        if (data.sadness !== undefined && this.sadnessBar && this.sadnessValue) {
            const sadnessPercent = Math.max(0, Math.min(100, data.sadness * 100));
            this.sadnessBar.style.width = `${sadnessPercent}%`;
            this.sadnessValue.textContent = data.sadness.toFixed(1);
        }
        
        // 更新恐惧
        if (data.fear !== undefined && this.fearBar && this.fearValue) {
            const fearPercent = Math.max(0, Math.min(100, data.fear * 100));
            this.fearBar.style.width = `${fearPercent}%`;
            this.fearValue.textContent = data.fear.toFixed(1);
        }
        
        // 更新信任
        if (data.trust !== undefined && this.trustBar && this.trustValue) {
            const trustPercent = Math.max(0, Math.min(100, data.trust * 100));
            this.trustBar.style.width = `${trustPercent}%`;
            this.trustValue.textContent = data.trust.toFixed(1);
        }
        
        // 更新期待
        if (data.expectation !== undefined && this.expectationBar && this.expectationValue) {
            const expectationPercent = Math.max(0, Math.min(100, data.expectation * 100));
            this.expectationBar.style.width = `${expectationPercent}%`;
            this.expectationValue.textContent = data.expectation.toFixed(1);
        }
        
        // 更新厌恶
        if (data.disgust !== undefined && this.disgustBar && this.disgustValue) {
            const disgustPercent = Math.max(0, Math.min(100, data.disgust * 100));
            this.disgustBar.style.width = `${disgustPercent}%`;
            this.disgustValue.textContent = data.disgust.toFixed(1);
        }
        
        // 更新惊讶
        if (data.surprise !== undefined && this.surpriseBar && this.surpriseValue) {
            const surprisePercent = Math.max(0, Math.min(100, data.surprise * 100));
            this.surpriseBar.style.width = `${surprisePercent}%`;
            this.surpriseValue.textContent = data.surprise.toFixed(1);
        }
        
        this.log('✅ 生理监控HUD更新完成');
    }
    
    // 发送WebSocket消息
    sendWebSocketMessage(data) {
        this.log('===== 开始发送WebSocket消息 =====');
        this.log('准备发送的消息:', data);
        
        // 检查WebSocket对象是否存在
        if (!this.websocket) {
            this.log('❌ WebSocket对象不存在，正在初始化...');
            this.initWebSocket();
            
            // 延迟发送消息，等待WebSocket初始化完成
            setTimeout(() => {
                this.sendWebSocketMessage(data);
            }, 1000);
            return;
        }
        
        // 检查WebSocket状态
        this.log('当前WebSocket状态:', this.websocket.readyState);
        this.log('WebSocket状态说明: 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED');
        
        if (this.websocket.readyState === WebSocket.OPEN) {
            try {
                const jsonData = JSON.stringify(data);
                this.websocket.send(jsonData);
                this.log('✅ 消息已通过WebSocket发送到后端');
                this.log('发送的JSON数据:', jsonData);
                this.log('===== WebSocket消息发送完成 =====');
            } catch (error) {
                this.log('❌ 消息发送失败:', error.message);
                this.log('错误堆栈:', error.stack);
            }
        } else if (this.websocket.readyState === WebSocket.CONNECTING) {
            this.log('⚠️ WebSocket正在连接中，将在连接成功后发送消息');
            // 等待连接成功后发送消息
            const sendOnOpen = () => {
                this.websocket.send(JSON.stringify(data));
                this.log('✅ 连接成功，已发送消息:', data);
                this.websocket.removeEventListener('open', sendOnOpen);
            };
            this.websocket.addEventListener('open', sendOnOpen);
        } else {
            this.log('❌ WebSocket未连接或已关闭，正在重新连接...');
            
            // 创建新的WebSocket连接
            this.websocket = new WebSocket(this.settings.backendUrl);
            
            // 设置连接事件
            this.websocket.onopen = () => {
                this.log('✅ WebSocket重新连接成功！');
                // 发送消息
                this.websocket.send(JSON.stringify(data));
                this.log('✅ 重新连接成功，已发送消息:', data);
            };
            
            this.websocket.onerror = (error) => {
                this.log('❌ WebSocket重新连接失败:', error.message);
            };
        }
        
        this.log('===== WebSocket消息发送流程完成 =====');
    }
    
    // 显示对话气泡
    showSpeechBubble(text, autoHide = true) {
        const bubble = document.getElementById('speech-bubble');
        if (!bubble) {
            this.log('⚠️ 找不到 speech-bubble 元素');
            return;
        }
        
        bubble.textContent = text;
        bubble.style.display = 'block';
        
        // 清除之前的自动隐藏定时器（如果存在）
        if (this.speechBubbleTimer) {
            clearTimeout(this.speechBubbleTimer);
            this.speechBubbleTimer = null;
        }
        
        // 如果 autoHide 为 true，3秒后自动隐藏
        if (autoHide) {
            this.speechBubbleTimer = setTimeout(() => {
                bubble.style.animation = 'fadeOut 0.3s ease';
                setTimeout(() => {
                    bubble.style.display = 'none';
                    bubble.style.animation = '';
                }, 300);
                this.speechBubbleTimer = null;
            }, 3000);
        }
    }
    
    // 播放动作
    playMotion(motionGroup, motionIndex) {
        if (!this.model || !this.model.motions) return;
        
        const motions = this.model.motions[motionGroup];
        if (motions && motions[motionIndex]) {
            this.model.motion(motionGroup, motionIndex);
        }
    }
    
    // 设置情绪
    setEmotion(emotion) {
        if (!this.model) return;
        this.triggerExpression(emotion).catch(error => {
            this.log(`⚠️ 设置情绪失败: ${error.message}`);
        });
    }
    
    // 测试对话气泡显示
    testSpeechBubble() {
        this.log('===== 开始测试对话气泡 =====');
        this.showSpeechBubble('测试对话气泡是否正常显示', true);
        this.log('对话气泡测试完成');
    }
    
    // 测试WebSocket连接
    testWebSocketConnection() {
        this.log('===== 开始测试WebSocket连接 =====');
        this.log(`当前环境: Electron=${this.isElectron}`);
        this.log(`当前WebSocket状态: ${this.websocket ? this.websocket.readyState : '未初始化'}`);
        
        // 强制重新初始化WebSocket
        this.initWebSocket();
        
        // 5秒后检查连接状态
        setTimeout(() => {
            this.log(`5秒后WebSocket状态: ${this.websocket ? this.websocket.readyState : '未初始化'}`);
            if (this.websocket) {
                this.log(`连接状态描述: ${this.getWebSocketStateDescription(this.websocket.readyState)}`);
            }
        }, 5000);
    }
    
    // 获取WebSocket状态描述
    getWebSocketStateDescription(state) {
        switch(state) {
            case WebSocket.CONNECTING:
                return 'CONNECTING (0) - 正在连接';
            case WebSocket.OPEN:
                return 'OPEN (1) - 连接成功';
            case WebSocket.CLOSING:
                return 'CLOSING (2) - 正在关闭';
            case WebSocket.CLOSED:
                return 'CLOSED (3) - 连接已关闭';
            default:
                return `UNKNOWN (${state}) - 未知状态`;
        }
    }
    
    // 触发表达式（统一方法）
    async triggerExpression(expressionName, buttonIndex = null) {
        if (!this.model) {
            this.log(`⚠️ 模型未加载，无法触发表达式`);
            return false;
        }
        
        // 移除文件扩展名（如果有）
        const cleanName = expressionName.replace(/\.exp3\.json$/i, '').replace(/\.json$/i, '');
        this.log(`尝试触发表达式: ${cleanName} (原始名称: ${expressionName})`);
        
        // 检查表达式管理器是否存在
        if (!this.model.internalModel || !this.model.internalModel.motionManager) {
            this.log(`⚠️ 模型内部管理器不存在`);
            return false;
        }
        
        const expressionManager = this.model.internalModel.motionManager.expressionManager;
        
        // 如果表达式管理器存在，使用标准方法
        if (expressionManager) {
            // 获取表达式定义列表
            const definitions = expressionManager.definitions || [];
            this.log(`找到 ${definitions.length} 个表达式定义:`, definitions.map((def, idx) => ({
                index: idx,
                file: def.File || def.file || 'N/A',
                name: def.Name || def.name || 'N/A'
            })));
            
            // 方法1: 尝试通过文件名匹配
            let matchedIndex = -1;
            for (let i = 0; i < definitions.length; i++) {
                const def = definitions[i];
                const defFile = def.File || def.file || '';
                const defName = def.Name || def.name || '';
                
                // 移除路径和扩展名进行比较
                const defFileBase = defFile.split('/').pop().split('\\').pop().replace(/\.exp3\.json$/i, '').replace(/\.json$/i, '');
                
                if (defFileBase === cleanName || defName === cleanName || 
                    defFile.includes(cleanName) || defName.includes(cleanName)) {
                    matchedIndex = i;
                    this.log(`✅ 找到匹配的表达式: 索引=${i}, 文件=${defFile}, 名称=${defName}`);
                    break;
                }
            }
            
            // 方法2: 如果没找到，尝试通过名称直接调用（库会自动匹配）
            if (matchedIndex === -1) {
                this.log(`尝试直接使用名称调用表达式: ${cleanName}`);
                try {
                    const result = await this.model.expression(cleanName);
                    if (result) {
                        this.log(`✅ 表达式 ${cleanName} 触发成功`);
                        return true;
                    } else {
                        this.log(`⚠️ 表达式 ${cleanName} 触发失败（返回false）`);
                    }
                } catch (error) {
                    this.log(`⚠️ 表达式调用异常: ${error.message}`);
                }
            } else {
                // 使用索引触发
                try {
                    const result = await this.model.expression(matchedIndex);
                    if (result) {
                        this.log(`✅ 表达式（索引 ${matchedIndex}）触发成功`);
                        return true;
                    } else {
                        this.log(`⚠️ 表达式（索引 ${matchedIndex}）触发失败（返回false）`);
                    }
                } catch (error) {
                    this.log(`⚠️ 表达式调用异常: ${error.message}`);
                }
            }
            
            // 如果都失败了，尝试使用原始名称
            if (matchedIndex === -1) {
                this.log(`尝试使用原始名称: ${expressionName}`);
                try {
                    const result = await this.model.expression(expressionName);
                    if (result) {
                        this.log(`✅ 表达式 ${expressionName} 触发成功`);
                        return true;
                    }
                } catch (error) {
                    this.log(`⚠️ 使用原始名称调用失败: ${error.message}`);
                }
            }
        } else {
            // 表达式管理器不存在，手动加载表达式文件
            this.log(`⚠️ 表达式管理器不存在，尝试手动加载表达式文件`);
            return await this.loadExpressionManually(expressionName, buttonIndex);
        }
        
        this.log(`❌ 无法触发表达式 ${expressionName}，请检查表达式文件是否正确配置`);
        return false;
    }
    
    // 手动加载表达式文件（当模型没有定义表达式时）
    async loadExpressionManually(expressionName, buttonIndex = null) {
        try {
            // 确保 defaultExpressionParams 和 buttonExpressionParams 已初始化
            if (!this.defaultExpressionParams || typeof this.defaultExpressionParams !== 'object') {
                this.defaultExpressionParams = {};
            }
            if (!this.buttonExpressionParams || typeof this.buttonExpressionParams !== 'object') {
                this.buttonExpressionParams = {};
            }
            if (buttonIndex !== null && buttonIndex !== undefined && !this.buttonExpressionParams[buttonIndex]) {
                this.buttonExpressionParams[buttonIndex] = {};
            }
            
            if (!this.model || !this.model.internalModel || !this.model.internalModel.coreModel) {
                this.log(`⚠️ 模型或核心模型不存在，无法手动加载表达式`);
                return false;
            }
            
            const modelName = this.settings.currentModel || 'openSource';
        const cleanName = expressionName.replace(/\.exp3\.json$/i, '').replace(/\.json$/i, '');
        
        // 在Electron环境中，使用fs模块读取文件；在浏览器环境中，使用fetch
        let expressionData = null;
        
        if (this.isElectron) {
            // Electron环境：使用fs模块
            try {
                const fs = require('fs');
                const path = require('path');
                
                // 获取应用根目录
                let appRoot;
                try {
                    const electron = require('electron');
                    if (electron.remote && electron.remote.app) {
                        appRoot = electron.remote.app.getAppPath();
                    } else if (electron.app) {
                        appRoot = electron.app.getAppPath();
                    } else if (typeof __dirname !== 'undefined') {
                        appRoot = __dirname;
                    } else {
                        appRoot = process.cwd();
                    }
                } catch (e) {
                    appRoot = typeof __dirname !== 'undefined' ? __dirname : process.cwd();
                }
                
                // 尝试多个可能的路径
                const possiblePaths = [
                    path.join(appRoot, 'models', modelName, `${cleanName}.exp3.json`),
                    path.join(appRoot, 'models', modelName, `${expressionName}.exp3.json`),
                    path.join(appRoot, 'models', modelName, 'expressions', `${cleanName}.exp3.json`),
                    path.join(appRoot, 'models', modelName, 'expressions', `${expressionName}.exp3.json`)
                ];
                
                for (const filePath of possiblePaths) {
                    try {
                        this.log(`尝试加载表达式文件: ${filePath}`);
                        if (fs.existsSync(filePath)) {
                            const fileContent = fs.readFileSync(filePath, 'utf8');
                            expressionData = JSON.parse(fileContent);
                            this.log(`✅ 成功从文件系统加载表达式: ${filePath}`);
                            break;
                        }
                    } catch (error) {
                        this.log(`⚠️ 读取文件失败 ${filePath}: ${error.message}`);
                        continue;
                    }
                }
            } catch (error) {
                this.log(`⚠️ Electron文件系统访问失败: ${error.message}`);
            }
        }
        
        // 如果Electron方式失败或不在Electron环境，尝试使用fetch
        if (!expressionData) {
            const possiblePaths = [
                `./models/${modelName}/${cleanName}.exp3.json`,
                `./models/${modelName}/${expressionName}.exp3.json`,
                `./models/${modelName}/expressions/${cleanName}.exp3.json`,
                `./models/${modelName}/expressions/${expressionName}.exp3.json`
            ];
            
            for (const urlPath of possiblePaths) {
                try {
                    this.log(`尝试通过fetch加载表达式文件: ${urlPath}`);
                    const response = await fetch(urlPath);
                    
                    if (!response.ok) {
                        continue; // 尝试下一个路径
                    }
                    
                    expressionData = await response.json();
                    this.log(`✅ 成功通过fetch加载表达式: ${urlPath}`);
                    break;
                } catch (error) {
                    this.log(`⚠️ fetch加载失败 ${urlPath}: ${error.message}`);
                    continue;
                }
            }
        }
        
        // 如果成功加载了表达式数据
        if (expressionData) {
            if (expressionData.Type === 'Live2D Expression' && expressionData.Parameters) {
                // 应用表达式参数到模型
                const coreModel = this.model.internalModel.coreModel;
                const parameters = expressionData.Parameters;
                
                this.log(`找到 ${parameters.length} 个表达式参数，开始应用...`);
                
                // 确保 defaultExpressionParams 是对象
                if (!this.defaultExpressionParams || typeof this.defaultExpressionParams !== 'object') {
                    this.defaultExpressionParams = {};
                }
                
                // 这段代码已经被上面的按钮索引检查逻辑替代，删除以避免重复
                
                // 保存当前参数值作为默认值（如果还没有保存）
                if (Object.keys(this.defaultExpressionParams).length === 0) {
                    this.log('保存当前参数值作为默认值...');
                    for (const param of parameters) {
                        const paramId = param.Id;
                        try {
                            let defaultValue = 0;
                            if (typeof coreModel.getParameterValueById === 'function') {
                                defaultValue = coreModel.getParameterValueById(paramId);
                                if (defaultValue === undefined || defaultValue === null) {
                                    defaultValue = 0;
                                }
                            } else if (typeof coreModel.getParamFloat === 'function') {
                                defaultValue = coreModel.getParamFloat(paramId);
                                if (defaultValue === undefined || defaultValue === null) {
                                    defaultValue = 0;
                                }
                            }
                            this.defaultExpressionParams[paramId] = defaultValue;
                        } catch (e) {
                            // 忽略无法获取的参数，使用默认值0
                            this.defaultExpressionParams[paramId] = 0;
                        }
                    }
                }
                
                // 如果指定了按钮索引，先重置该按钮之前的表达式参数（如果有）
                if (buttonIndex !== null && buttonIndex !== undefined) {
                    // 确保 buttonExpressionParams 已初始化
                    if (!this.buttonExpressionParams || typeof this.buttonExpressionParams !== 'object') {
                        this.buttonExpressionParams = {};
                    }
                    const previousParams = this.buttonExpressionParams[buttonIndex];
                    if (previousParams && typeof previousParams === 'object' && Object.keys(previousParams).length > 0) {
                        this.log(`检测到按钮 ${buttonIndex} 之前应用的表达式参数，先重置...`);
                        // 先重置该按钮之前的参数（反向应用）
                        for (const [paramId, value] of Object.entries(previousParams)) {
                            try {
                                if (typeof coreModel.getParameterValueById === 'function' && typeof coreModel.setParameterValueById === 'function') {
                                    const currentValue = coreModel.getParameterValueById(paramId);
                                    if (currentValue !== undefined && currentValue !== null) {
                                        coreModel.setParameterValueById(paramId, currentValue - value);
                                    }
                                } else if (typeof coreModel.getParamFloat === 'function' && typeof coreModel.setParamFloat === 'function') {
                                    const currentValue = coreModel.getParamFloat(paramId);
                                    if (currentValue !== undefined && currentValue !== null) {
                                        coreModel.setParamFloat(paramId, currentValue - value);
                                    }
                                }
                            } catch (e) {
                                // 参数不存在，忽略
                            }
                        }
                    }
                    // 清空该按钮的参数记录，准备记录新的表达式参数
                    this.buttonExpressionParams[buttonIndex] = {};
                }
                
                for (const param of parameters) {
                    const paramId = param.Id;
                    const paramValue = param.Value || 0;
                    const blend = param.Blend || 'Multiply';
                    
                    try {
                        // Cubism 4 API
                        if (typeof coreModel.setParameterValueById === 'function' && typeof coreModel.getParameterValueById === 'function') {
                            let currentValue = 0;
                            try {
                                currentValue = coreModel.getParameterValueById(paramId);
                                if (currentValue === undefined || currentValue === null) {
                                    currentValue = this.defaultExpressionParams[paramId] || 0;
                                }
                            } catch (e) {
                                currentValue = this.defaultExpressionParams[paramId] || 0;
                            }
                            
                            if (blend === 'Add') {
                                // 加法混合：获取当前值并加上新值
                                const newValue = currentValue + paramValue;
                                coreModel.setParameterValueById(paramId, newValue);
                                // 记录应用的增量值，用于重置（如果指定了按钮索引）
                                if (buttonIndex !== null && buttonIndex !== undefined) {
                                    if (!this.buttonExpressionParams[buttonIndex]) {
                                        this.buttonExpressionParams[buttonIndex] = {};
                                    }
                                    this.buttonExpressionParams[buttonIndex][paramId] = (this.buttonExpressionParams[buttonIndex][paramId] || 0) + paramValue;
                                }
                            } else {
                                // 乘法混合或其他：直接设置值
                                coreModel.setParameterValueById(paramId, paramValue);
                                // 记录应用的绝对值，用于重置（如果指定了按钮索引）
                                if (buttonIndex !== null && buttonIndex !== undefined) {
                                    if (!this.buttonExpressionParams[buttonIndex]) {
                                        this.buttonExpressionParams[buttonIndex] = {};
                                    }
                                    this.buttonExpressionParams[buttonIndex][paramId] = paramValue;
                                }
                            }
                        } else if (typeof coreModel.setParamFloat === 'function' && typeof coreModel.getParamFloat === 'function') {
                            // Cubism 2 API
                            let currentValue = 0;
                            try {
                                currentValue = coreModel.getParamFloat(paramId);
                                if (currentValue === undefined || currentValue === null) {
                                    currentValue = this.defaultExpressionParams[paramId] || 0;
                                }
                            } catch (e) {
                                currentValue = this.defaultExpressionParams[paramId] || 0;
                            }
                            
                            if (blend === 'Add') {
                                const newValue = currentValue + paramValue;
                                coreModel.setParamFloat(paramId, newValue);
                                // 记录应用的增量值，用于重置（如果指定了按钮索引）
                                if (buttonIndex !== null && buttonIndex !== undefined) {
                                    if (!this.buttonExpressionParams[buttonIndex]) {
                                        this.buttonExpressionParams[buttonIndex] = {};
                                    }
                                    this.buttonExpressionParams[buttonIndex][paramId] = (this.buttonExpressionParams[buttonIndex][paramId] || 0) + paramValue;
                                }
                            } else {
                                coreModel.setParamFloat(paramId, paramValue);
                                // 记录应用的绝对值，用于重置（如果指定了按钮索引）
                                if (buttonIndex !== null && buttonIndex !== undefined) {
                                    if (!this.buttonExpressionParams[buttonIndex]) {
                                        this.buttonExpressionParams[buttonIndex] = {};
                                    }
                                    this.buttonExpressionParams[buttonIndex][paramId] = paramValue;
                                }
                            }
                        } else {
                            this.log(`⚠️ 模型不支持参数操作 API`);
                        }
                    } catch (error) {
                        this.log(`⚠️ 设置参数 ${paramId} 失败: ${error.message}`);
                        console.error('参数设置错误详情:', error);
                    }
                }
                
                this.log(`✅ 表达式 ${cleanName} 手动加载并应用成功`);
                return true;
            } else {
                this.log(`⚠️ 表达式文件格式不正确，Type: ${expressionData.Type}, Parameters: ${expressionData.Parameters ? '存在' : '不存在'}`);
            }
        } else {
            this.log(`❌ 无法找到或加载表达式文件: ${expressionName}`);
        }
        
        return false;
        } catch (error) {
            this.log(`⚠️ 手动加载表达式时发生错误: ${error.message}`);
            console.error('表达式加载错误详情:', error);
            console.error('错误堆栈:', error.stack);
            return false;
        }
    }
    
    // 预留的唇形同步函数
    updateMouth(value) {
        if (!this.model || !this.model.internalModel) return;
        
        // 根据音频振幅控制嘴巴张合
        value = Math.max(0, Math.min(1, value));
        this.model.internalModel.setParamFloat('ParamMouthOpenY', value);
    }
    
    // 初始化设置菜单
    initSettingsMenu() {
        // 初始化API配置管理
        this.initAPIConfigManager();
        
        // 加载保存的设置到UI
        const backendUrlInput = document.getElementById('backend-url');
        const modelScaleSlider = document.getElementById('model-scale');
        const scaleValue = document.getElementById('scale-value');
        const volumeSlider = document.getElementById('volume');
        const volumeValue = document.getElementById('volume-value');
        const debugToggle = document.getElementById('debug-mode');
        
        if (backendUrlInput) {
            backendUrlInput.value = this.settings.backendUrl || 'ws://127.0.0.1:8766';
        }
        if (modelScaleSlider && scaleValue) {
            modelScaleSlider.value = this.settings.modelScale || 1.0;
            scaleValue.textContent = this.settings.modelScale || 1.0;
        }
        if (volumeSlider && volumeValue) {
            volumeSlider.value = this.settings.volume || 50;
            volumeValue.textContent = this.settings.volume || 50;
        }
        if (debugToggle) {
            debugToggle.checked = this.settings.debugMode || false;
        }
        
        // 绑定设置菜单事件
        document.getElementById('save-settings').addEventListener('click', () => {
            this.saveSettings();
        });
        
        document.getElementById('close-settings').addEventListener('click', () => {
            this.toggleSettingsMenu();
        });
        
        // 初始化模型选择下拉框
        this.initModelSelector();
        
        // 初始化窗口大小设置
        this.initWindowSizeSettings();
        
        // 初始化表情配置
        this.initExpressionConfigs();
        
        // 绑定滑块事件
        const scaleSlider = document.getElementById('model-scale');
        const scaleValueDisplay = document.getElementById('scale-value');
        scaleSlider.addEventListener('input', (event) => {
            const value = parseFloat(event.target.value);
            scaleValueDisplay.textContent = value;
            this.settings.modelScale = value;
            
            // 更新模型缩放
            if (this.model) {
                this.model.scale.set(value);
                this.centerModel();
            }
        });
        
        const volumeSliderInput = document.getElementById('volume');
        const volumeValueDisplay = document.getElementById('volume-value');
        volumeSliderInput.addEventListener('input', (event) => {
            const value = parseInt(event.target.value);
            volumeValueDisplay.textContent = value;
            this.settings.volume = value;
            
            // 发送音量更新
            this.sendWebSocketMessage({ type: 'volume', volume: value });
        });
        
        // 绑定调试模式切换
        const debugToggleInput = document.getElementById('debug-mode');
        debugToggleInput.addEventListener('change', (event) => {
            this.settings.debugMode = event.target.checked;
            this.toggleDebugLogs();
        });
        
        // 初始化Electron特有设置
        this.initElectronSettings();
    }
    
    // 初始化模型选择器
    initModelSelector() {
        const modelSelect = document.getElementById('model-select');
        if (!modelSelect) return;
        
        // 设置当前选择的模型
        modelSelect.value = this.settings.currentModel || 'openSource';
        
        // 在 Electron 环境中扫描 models 目录
        if (this.isElectron) {
            try {
                const fs = require('fs');
                const path = require('path');
                // 在 Electron 中，使用 process.cwd() 获取应用根目录
                const appRoot = process.cwd ? process.cwd() : (typeof __dirname !== 'undefined' ? __dirname : '.');
                const modelsDir = path.join(appRoot, 'models');
                
                if (fs.existsSync(modelsDir)) {
                    const modelDirs = fs.readdirSync(modelsDir).filter(item => {
                        const itemPath = path.join(modelsDir, item);
                        return fs.statSync(itemPath).isDirectory();
                    });
                    
                    // 清空现有选项
                    modelSelect.innerHTML = '';
                    
                    // 添加扫描到的模型
                    modelDirs.forEach(modelName => {
                        const option = document.createElement('option');
                        option.value = modelName;
                        option.textContent = modelName;
                        modelSelect.appendChild(option);
                    });
                    
                    // 设置当前选择的模型
                    if (modelDirs.includes(this.settings.currentModel)) {
                        modelSelect.value = this.settings.currentModel;
                    } else if (modelDirs.length > 0) {
                        modelSelect.value = modelDirs[0];
                        this.settings.currentModel = modelDirs[0];
                    }
                    
                    this.log(`扫描到 ${modelDirs.length} 个模型: ${modelDirs.join(', ')}`);
                } else {
                    this.log('⚠️ models 目录不存在');
                }
            } catch (error) {
                this.log('⚠️ 扫描 models 目录失败:', error.message);
            }
        }
        
        // 绑定模型切换事件
        modelSelect.addEventListener('change', (event) => {
            const selectedModel = event.target.value;
            if (selectedModel !== this.settings.currentModel) {
                this.log(`切换模型: ${this.settings.currentModel} -> ${selectedModel}`);
                this.settings.currentModel = selectedModel;
                
                // 更新表情配置UI
                this.scanModelExpressions(selectedModel);
                this.updateExpressionButtonsForModel(selectedModel);
                
                // 更新配置输入框的值
                const config = this.expressionButtonsConfig[selectedModel] || [];
                for (let i = 0; i < 8; i++) {
                    const nameInput = document.getElementById(`expr-name-${i}`);
                    const fileSelect = document.getElementById(`expr-file-${i}`);
                    if (nameInput) {
                        nameInput.value = config[i]?.name || `表情${i + 1}`;
                    }
                    if (fileSelect && config[i]?.file) {
                        fileSelect.value = config[i].file;
                    }
                }
                
                this.switchModel(selectedModel);
            }
        });
    }
    
    // 初始化窗口大小设置
    initWindowSizeSettings() {
        if (!this.isElectron) return;
        
        const widthSlider = document.getElementById('window-width');
        const heightSlider = document.getElementById('window-height');
        const widthValue = document.getElementById('width-value');
        const heightValue = document.getElementById('height-value');
        
        if (!widthSlider || !heightSlider) return;
        
        // 加载保存的窗口大小
        const savedWidth = localStorage.getItem('nuwa_window_width');
        const savedHeight = localStorage.getItem('nuwa_window_height');
        
        if (savedWidth) {
            widthSlider.value = savedWidth;
            widthValue.textContent = savedWidth;
        }
        if (savedHeight) {
            heightSlider.value = savedHeight;
            heightValue.textContent = savedHeight;
        }
        
        // 绑定窗口宽度滑块
        widthSlider.addEventListener('input', (event) => {
            const value = parseInt(event.target.value);
            widthValue.textContent = value;
            if (this.isElectron && this.ipcRenderer) {
                this.ipcRenderer.send('resize-window', value, parseInt(heightSlider.value));
            }
        });
        
        // 绑定窗口高度滑块
        heightSlider.addEventListener('input', (event) => {
            const value = parseInt(event.target.value);
            heightValue.textContent = value;
            if (this.isElectron && this.ipcRenderer) {
                this.ipcRenderer.send('resize-window', parseInt(widthSlider.value), value);
            }
        });
    }
    
    // 初始化表情配置
    initExpressionConfigs() {
        const configsContainer = document.getElementById('expression-configs');
        if (!configsContainer) return;
        
        // 加载保存的配置
        this.loadExpressionConfigs();
        
        // 生成8个配置项
        for (let i = 0; i < 8; i++) {
            const configItem = document.createElement('div');
            configItem.className = 'expression-config-item';
            configItem.innerHTML = `
                <label>按钮 ${i + 1}</label>
                <div class="expression-config-row">
                    <input type="text" 
                           id="expr-name-${i}" 
                           placeholder="按钮名称" 
                           value="${this.expressionButtonsConfig[this.settings.currentModel]?.[i]?.name || `表情${i + 1}`}">
                    <select id="expr-file-${i}">
                        <option value="">-- 未选择 --</option>
                    </select>
                </div>
            `;
            configsContainer.appendChild(configItem);
        }
        
        // 扫描当前模型的表达式文件
        this.scanModelExpressions(this.settings.currentModel || 'openSource');
        
        // 绑定输入事件，实时更新按钮显示
        for (let i = 0; i < 8; i++) {
            const nameInput = document.getElementById(`expr-name-${i}`);
            const fileSelect = document.getElementById(`expr-file-${i}`);
            
            if (nameInput) {
                nameInput.addEventListener('input', () => {
                    this.updateExpressionButton(i);
                    this.saveExpressionConfigs();
                });
            }
            
            if (fileSelect) {
                fileSelect.addEventListener('change', () => {
                    this.updateExpressionButton(i);
                    this.saveExpressionConfigs();
                });
            }
        }
    }
    
    // 扫描模型的表达式文件
    scanModelExpressions(modelName) {
        if (!this.isElectron) {
            // 非Electron环境，使用默认列表
            this.updateExpressionSelects([]);
            return;
        }
        
        try {
            const fs = require('fs');
            const path = require('path');
            
            // 在Electron中获取应用路径
            let appRoot;
            try {
                // 尝试使用electron的remote模块获取应用路径
                const electron = require('electron');
                if (electron.remote && electron.remote.app) {
                    appRoot = electron.remote.app.getAppPath();
                } else if (electron.app) {
                    // 在主进程中
                    appRoot = electron.app.getAppPath();
                } else {
                    // 如果remote不可用，使用__dirname（相对于index.html的位置）
                    // 在渲染进程中，__dirname指向index.html所在的目录
                    if (typeof __dirname !== 'undefined') {
                        appRoot = __dirname;
                    } else if (typeof process !== 'undefined' && process.cwd) {
                        appRoot = process.cwd();
                    } else {
                        appRoot = '.';
                    }
                }
            } catch (e) {
                // 如果上述方法都失败，使用__dirname或process.cwd()
                if (typeof __dirname !== 'undefined') {
                    appRoot = __dirname;
                } else if (typeof process !== 'undefined' && process.cwd) {
                    appRoot = process.cwd();
                } else {
                    appRoot = '.';
                }
                this.log('使用备用方法获取应用路径:', appRoot);
            }
            
            const modelDir = path.join(appRoot, 'models', modelName);
            const expressionsDir = path.join(modelDir, 'expressions');
            
            this.log(`扫描表达式文件，应用根目录: ${appRoot}`);
            this.log(`模型目录: ${modelDir}`);
            this.log(`表达式目录: ${expressionsDir}`);
            
            // 获取所有表达式文件
            let expressionFiles = [];
            
            // 1. 检查 expressions 子目录
            if (fs.existsSync(expressionsDir) && fs.statSync(expressionsDir).isDirectory()) {
                const files = fs.readdirSync(expressionsDir)
                    .filter(file => {
                        const filePath = path.join(expressionsDir, file);
                        try {
                            return fs.statSync(filePath).isFile() && file.endsWith('.exp3.json');
                        } catch (e) {
                            return false;
                        }
                    })
                    .map(file => file.replace('.exp3.json', ''));
                expressionFiles.push(...files);
                this.log(`在expressions目录中找到 ${files.length} 个表达式文件: ${files.join(', ')}`);
            } else {
                this.log(`expressions目录不存在: ${expressionsDir}`);
            }
            
            // 2. 检查模型根目录下的 .exp3.json 文件
            if (fs.existsSync(modelDir) && fs.statSync(modelDir).isDirectory()) {
                const rootFiles = fs.readdirSync(modelDir)
                    .filter(file => {
                        const filePath = path.join(modelDir, file);
                        try {
                            return fs.statSync(filePath).isFile() && file.endsWith('.exp3.json');
                        } catch (e) {
                            return false;
                        }
                    })
                    .map(file => file.replace('.exp3.json', ''));
                expressionFiles.push(...rootFiles);
                this.log(`在模型根目录中找到 ${rootFiles.length} 个表达式文件: ${rootFiles.join(', ')}`);
            } else {
                this.log(`模型目录不存在: ${modelDir}`);
            }
            
            // 去重并排序
            expressionFiles = [...new Set(expressionFiles)].sort();
            
            this.log(`扫描模型 ${modelName}，总共找到 ${expressionFiles.length} 个表达式文件: ${expressionFiles.join(', ')}`);
            
            // 更新所有下拉框
            this.updateExpressionSelects(expressionFiles, modelName);
        } catch (error) {
            this.log('⚠️ 扫描表达式文件失败:', error.message);
            console.error('扫描表达式文件错误详情:', error);
            console.error('错误堆栈:', error.stack);
            this.updateExpressionSelects([]);
        }
    }
    
    // 更新表达式选择下拉框
    updateExpressionSelects(expressionFiles, modelName) {
        modelName = modelName || this.settings.currentModel || 'openSource';
        
        for (let i = 0; i < 8; i++) {
            const fileSelect = document.getElementById(`expr-file-${i}`);
            if (!fileSelect) continue;
            
            // 保存当前选择的值
            const currentValue = fileSelect.value;
            
            // 清空并重新填充选项
            fileSelect.innerHTML = '<option value="">-- 未选择 --</option>';
            expressionFiles.forEach(file => {
                const option = document.createElement('option');
                option.value = file;
                option.textContent = file;
                fileSelect.appendChild(option);
            });
            
            // 恢复之前的选择或加载保存的配置
            const savedConfig = this.expressionButtonsConfig[modelName]?.[i];
            if (savedConfig && savedConfig.file) {
                fileSelect.value = savedConfig.file;
            } else if (currentValue && expressionFiles.includes(currentValue)) {
                fileSelect.value = currentValue;
            }
        }
    }
    
    // 加载表情配置
    loadExpressionConfigs() {
        try {
            const saved = localStorage.getItem('nuwa_expression_configs');
            if (saved) {
                this.expressionButtonsConfig = JSON.parse(saved);
            }
        } catch (error) {
            this.log('⚠️ 加载表情配置失败:', error.message);
            this.expressionButtonsConfig = {};
        }
    }
    
    // 保存表情配置
    saveExpressionConfigs() {
        const modelName = this.settings.currentModel || 'openSource';
        
        if (!this.expressionButtonsConfig[modelName]) {
            this.expressionButtonsConfig[modelName] = [];
        }
        
        // 收集当前配置
        for (let i = 0; i < 8; i++) {
            const nameInput = document.getElementById(`expr-name-${i}`);
            const fileSelect = document.getElementById(`expr-file-${i}`);
            
            if (nameInput && fileSelect) {
                this.expressionButtonsConfig[modelName][i] = {
                    name: nameInput.value || `表情${i + 1}`,
                    file: fileSelect.value || ''
                };
            }
        }
        
        // 保存到localStorage
        try {
            localStorage.setItem('nuwa_expression_configs', JSON.stringify(this.expressionButtonsConfig));
            this.log('表情配置已保存');
        } catch (error) {
            this.log('⚠️ 保存表情配置失败:', error.message);
        }
        
        // 更新按钮显示
        this.updateExpressionButtonsForModel(modelName);
    }
    
    // 更新单个表情按钮
    updateExpressionButton(index) {
        const modelName = this.settings.currentModel || 'openSource';
        const nameInput = document.getElementById(`expr-name-${index}`);
        const fileSelect = document.getElementById(`expr-file-${index}`);
        
        if (nameInput && fileSelect) {
            const button = document.querySelector(`.expression-btn[data-index="${index}"]`);
            if (button) {
                button.textContent = nameInput.value || `表情${index + 1}`;
                button.title = fileSelect.value ? `表达式: ${fileSelect.value}` : '点击设置';
            }
        }
    }
    
    // 更新表情按钮的激活状态
    updateExpressionButtonState(index, isActive) {
        const button = document.querySelector(`.expression-btn[data-index="${index}"]`);
        if (button) {
            if (isActive) {
                button.classList.add('active');
                button.style.background = 'rgba(100, 200, 255, 0.3)';
            } else {
                button.classList.remove('active');
                button.style.background = '';
            }
        }
    }
    
    // 重置表达式（恢复默认状态）
    resetExpression() {
        if (!this.model || !this.model.internalModel || !this.model.internalModel.coreModel) {
            this.log('⚠️ 模型未加载，无法重置表达式');
            return;
        }
        
        const expressionManager = this.model.internalModel.motionManager?.expressionManager;
        const coreModel = this.model.internalModel.coreModel;
        
        if (expressionManager) {
            // 如果有表达式管理器，使用标准方法重置
            try {
                // 停止所有表达式
                if (expressionManager.queueManager) {
                    expressionManager.queueManager.stopAllMotions();
                }
                
                // 使用 resetExpression 重置到默认表达式
                expressionManager.resetExpression();
                this.log('✅ 已通过表达式管理器重置表达式');
            } catch (error) {
                this.log(`⚠️ 通过表达式管理器重置失败: ${error.message}`);
                // 如果标准方法失败，尝试手动重置
                this.resetExpressionManually();
            }
        } else {
            // 如果没有表达式管理器，手动重置所有参数
            this.resetExpressionManually();
        }
    }
    
    // 手动重置表达式参数
    resetExpressionManually() {
        if (!this.model || !this.model.internalModel || !this.model.internalModel.coreModel) {
            return;
        }
        
        const coreModel = this.model.internalModel.coreModel;
        
        try {
            this.log('开始手动重置表达式参数...');
            
            // 确保 defaultExpressionParams 和 buttonExpressionParams 是对象
            if (!this.defaultExpressionParams || typeof this.defaultExpressionParams !== 'object') {
                this.defaultExpressionParams = {};
            }
            if (!this.buttonExpressionParams || typeof this.buttonExpressionParams !== 'object') {
                this.buttonExpressionParams = {};
            }
            
            // 如果有保存的默认参数，恢复它们
            if (Object.keys(this.defaultExpressionParams).length > 0) {
                this.log(`恢复 ${Object.keys(this.defaultExpressionParams).length} 个默认参数`);
                for (const [paramId, defaultValue] of Object.entries(this.defaultExpressionParams)) {
                    try {
                        if (typeof coreModel.setParameterValueById === 'function') {
                            coreModel.setParameterValueById(paramId, defaultValue);
                        } else if (typeof coreModel.setParamFloat === 'function') {
                            coreModel.setParamFloat(paramId, defaultValue);
                        }
                    } catch (e) {
                        // 参数不存在，忽略
                    }
                }
                this.log('✅ 已恢复默认参数值');
                return;
            }
            
            // 如果没有保存默认参数，尝试重置所有按钮的表达式参数
            let hasResetAny = false;
            for (const [btnIndex, buttonParams] of Object.entries(this.buttonExpressionParams)) {
                if (buttonParams && Object.keys(buttonParams).length > 0) {
                    this.log(`反向应用按钮 ${btnIndex} 的 ${Object.keys(buttonParams).length} 个表达式参数`);
                    for (const [paramId, value] of Object.entries(buttonParams)) {
                        try {
                            if (typeof coreModel.setParameterValueById === 'function') {
                                const currentValue = coreModel.getParameterValueById(paramId);
                                if (currentValue !== undefined && currentValue !== null) {
                                    coreModel.setParameterValueById(paramId, currentValue - value);
                                }
                            } else if (typeof coreModel.setParamFloat === 'function') {
                                const currentValue = coreModel.getParamFloat(paramId);
                                if (currentValue !== undefined && currentValue !== null) {
                                    coreModel.setParamFloat(paramId, currentValue - value);
                                }
                            }
                        } catch (e) {
                            // 参数不存在，忽略
                        }
                    }
                    hasResetAny = true;
                }
            }
            if (hasResetAny) {
                this.buttonExpressionParams = {};
                this.log('✅ 已反向应用所有按钮的表达式参数');
                return;
            }
            
            // 如果都没有，尝试重置常见的表情相关参数到默认值
            this.log('尝试重置常见表情参数到默认值');
            const commonParams = {
                'ParamEyeLOpen': 1.0,
                'ParamEyeROpen': 1.0,
                'ParamMouthOpenY': 0.0,
                'ParamMouthForm': 0.0,
                'ParamBrowLY': 0.0,
                'ParamBrowRY': 0.0
            };
            
            for (const [paramId, defaultValue] of Object.entries(commonParams)) {
                try {
                    if (typeof coreModel.setParameterValueById === 'function') {
                        coreModel.setParameterValueById(paramId, defaultValue);
                    } else if (typeof coreModel.setParamFloat === 'function') {
                        coreModel.setParamFloat(paramId, defaultValue);
                    }
                } catch (e) {
                    // 参数不存在，忽略
                }
            }
            
            this.log('✅ 已重置常见表情参数');
        } catch (error) {
            this.log(`⚠️ 手动重置表达式失败: ${error.message}`);
            console.error('重置表达式错误详情:', error);
        }
    }
    
    // 更新模型的表情按钮显示
    updateExpressionButtonsForModel(modelName) {
        const config = this.expressionButtonsConfig[modelName] || [];
        
        for (let i = 0; i < 8; i++) {
            const button = document.querySelector(`.expression-btn[data-index="${i}"]`);
            if (button) {
                const btnConfig = config[i] || { name: `表情${i + 1}`, file: '' };
                button.textContent = btnConfig.name;
                button.title = btnConfig.file ? `表达式: ${btnConfig.file}` : '点击设置';
            }
        }
    }
    
    // 初始化表达式按钮
    initExpressionButtons() {
        // 加载保存的配置
        this.loadExpressionConfigs();
        
        // 初始化按钮显示
        this.updateExpressionButtonsForModel(this.settings.currentModel || 'openSource');
        
        // 绑定点击事件
        for (let i = 0; i < 8; i++) {
            const button = document.querySelector(`.expression-btn[data-index="${i}"]`);
            if (button) {
                // 移除旧的事件监听器（如果有）
                const newButton = button.cloneNode(true);
                button.parentNode.replaceChild(newButton, button);
                
                newButton.addEventListener('click', (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    event.stopImmediatePropagation();
                    
                    this.log(`表情按钮 ${i} 被点击`);
                    
                    const modelName = this.settings.currentModel || 'openSource';
                    const config = this.expressionButtonsConfig[modelName] || [];
                    const btnConfig = config[i];
                    
                    // 确定要使用的表达式文件名
                    let expressionFile = null;
                    if (btnConfig && btnConfig.file) {
                        expressionFile = btnConfig.file;
                        this.log(`使用配置的表达式文件: ${expressionFile}`);
                    } else if (btnConfig && btnConfig.name) {
                        // 如果没有配置 file，尝试使用按钮名称作为表达式文件名
                        expressionFile = btnConfig.name;
                        this.log(`使用按钮名称作为表达式文件: ${expressionFile}`);
                    } else {
                        // 如果连配置都没有，使用按钮文本
                        const buttonText = newButton.textContent.trim();
                        if (buttonText && buttonText !== `表情${i + 1}`) {
                            expressionFile = buttonText;
                            this.log(`使用按钮文本作为表达式文件: ${expressionFile}`);
                        }
                    }
                    
                    if (expressionFile && this.model) {
                        // 检查当前按钮是否已激活
                        const isCurrentlyActive = this.activeExpressionButtons[i] === true;
                        
                        if (isCurrentlyActive) {
                            // 如果按钮已激活，则取消该按钮的表情
                            this.log(`取消表情按钮 ${i} 的激活状态`);
                            this.resetExpressionForButton(i);
                            this.activeExpressionButtons[i] = false;
                            this.updateExpressionButtonState(i, false);
                        } else {
                            // 如果按钮未激活，则激活该按钮的表情
                            this.log(`激活表情按钮 ${i}`);
                            this.applyNewExpression(expressionFile, i);
                        }
                    } else {
                        // 如果没有配置且没有模型，打开设置面板
                        if (!this.model) {
                            this.log(`⚠️ 模型未加载，无法触发表达式`);
                        } else {
                            this.log(`⚠️ 表情按钮 ${i} 未配置表达式文件，打开设置面板`);
                            this.log(`当前配置:`, btnConfig);
                            this.log(`按钮文本:`, newButton.textContent);
                        }
                        this.toggleSettingsMenu();
                    }
                }, true); // 使用捕获阶段
                
                // 确保按钮可以接收事件
                newButton.style.pointerEvents = 'auto';
                newButton.style.zIndex = '1001';
                newButton.style.position = 'relative';
            }
        }
    }
    
    // 应用新表达式的辅助方法
    applyNewExpression(expressionFile, buttonIndex) {
        this.log(`触发表达式: ${expressionFile} (按钮 ${buttonIndex})`);
        this.triggerExpression(expressionFile, buttonIndex).then(success => {
            if (success) {
                this.activeExpressionButtons[buttonIndex] = true;
                this.updateExpressionButtonState(buttonIndex, true);
                this.log(`✅ 表情按钮 ${buttonIndex} 激活成功`);
            } else {
                this.log(`⚠️ 表情按钮 ${buttonIndex} 触发失败（返回false）`);
            }
        }).catch(error => {
            this.log(`⚠️ 触发表达式失败: ${error.message}`);
            console.error('表达式触发错误详情:', error);
        });
    }
    
    // 重置指定按钮的表达式
    resetExpressionForButton(buttonIndex) {
        if (!this.model || !this.model.internalModel || !this.model.internalModel.coreModel) {
            this.log(`⚠️ 模型未加载，无法重置按钮 ${buttonIndex} 的表达式`);
            return;
        }
        
        const coreModel = this.model.internalModel.coreModel;
        const buttonParams = this.buttonExpressionParams[buttonIndex];
        
        if (!buttonParams || Object.keys(buttonParams).length === 0) {
            this.log(`⚠️ 按钮 ${buttonIndex} 没有保存的表达式参数`);
            return;
        }
        
        try {
            this.log(`重置按钮 ${buttonIndex} 的表达式参数...`);
            
            // 反向应用该按钮的参数
            for (const [paramId, value] of Object.entries(buttonParams)) {
                try {
                    if (typeof coreModel.getParameterValueById === 'function' && typeof coreModel.setParameterValueById === 'function') {
                        const currentValue = coreModel.getParameterValueById(paramId);
                        if (currentValue !== undefined && currentValue !== null) {
                            coreModel.setParameterValueById(paramId, currentValue - value);
                        }
                    } else if (typeof coreModel.getParamFloat === 'function' && typeof coreModel.setParamFloat === 'function') {
                        const currentValue = coreModel.getParamFloat(paramId);
                        if (currentValue !== undefined && currentValue !== null) {
                            coreModel.setParamFloat(paramId, currentValue - value);
                        }
                    }
                } catch (e) {
                    // 参数不存在，忽略
                }
            }
            
            // 清除该按钮的参数记录
            delete this.buttonExpressionParams[buttonIndex];
            this.log(`✅ 按钮 ${buttonIndex} 的表达式已重置`);
        } catch (error) {
            this.log(`⚠️ 重置按钮 ${buttonIndex} 的表达式失败: ${error.message}`);
            console.error('重置表达式错误详情:', error);
        }
    }
    
    // 初始化TTS控制
    initTTSControls() {
        const ttsEnabledCheckbox = document.getElementById('tts-enabled');
        const ttsModelSelect = document.getElementById('tts-model');
        const testTTSButton = document.getElementById('test-tts');
        const ttsStatusDisplay = document.getElementById('tts-status-display');
        const ttsStatusText = document.getElementById('tts-status-text');
        const ttsFeedback = document.getElementById('tts-feedback');
        
        if (!ttsEnabledCheckbox || !ttsModelSelect || !testTTSButton) {
            this.log('⚠️ TTS控制元素未找到');
            return;
        }
        
        // 加载保存的TTS设置
        ttsEnabledCheckbox.checked = this.settings.ttsEnabled;
        ttsModelSelect.value = this.settings.ttsModel;
        
        // 更新TTS状态显示
        this.updateTTSStatusDisplay();
        
        // TTS开关事件
        ttsEnabledCheckbox.addEventListener('change', (e) => {
            const enabled = e.target.checked;
            this.settings.ttsEnabled = enabled;
            this.saveSettings();
            this.sendTTSConfig();
            this.updateTTSStatusDisplay();
            this.showTTSFeedback(enabled ? 'TTS已启用' : 'TTS已禁用', 'info');
        });
        
        // TTS模型选择事件
        ttsModelSelect.addEventListener('change', (e) => {
            this.settings.ttsModel = e.target.value;
            this.saveSettings();
            this.sendTTSConfig();
            this.showTTSFeedback(`TTS模型已切换为: ${e.target.value}`, 'info');
        });
        
        // TTS测试按钮事件
        testTTSButton.addEventListener('click', () => {
            this.testTTS();
        });
        
        this.log('✅ TTS控制初始化完成');
    }
    
    // 初始化Live2D控制
    initLive2DControls() {
        const live2dEnabledCheckbox = document.getElementById('live2d-enabled');
        const live2dStatus = document.getElementById('live2d-status');
        const toggleLive2DButton = document.getElementById('toggle-live2d');
        
        if (!live2dEnabledCheckbox || !live2dStatus || !toggleLive2DButton) {
            this.log('⚠️ Live2D控制元素未找到');
            return;
        }
        
        // 加载保存的Live2D设置
        live2dEnabledCheckbox.checked = this.settings.live2dEnabled;
        
        // 更新Live2D状态显示
        this.updateLive2DStatusDisplay();
        
        // Live2D开关事件
        live2dEnabledCheckbox.addEventListener('change', (e) => {
            const enabled = e.target.checked;
            this.settings.live2dEnabled = enabled;
            this.saveSettings();
            this.sendLive2DConfig();
            this.updateLive2DStatusDisplay();
            this.toggleLive2DDisplay(enabled);
        });
        
        // Live2D切换按钮事件
        toggleLive2DButton.addEventListener('click', () => {
            const newState = !this.settings.live2dEnabled;
            this.settings.live2dEnabled = newState;
            live2dEnabledCheckbox.checked = newState;
            this.saveSettings();
            this.sendLive2DConfig();
            this.updateLive2DStatusDisplay();
            this.toggleLive2DDisplay(newState);
        });
        
        this.log('✅ Live2D控制初始化完成');
    }
    
    // 发送Live2D配置到服务器
    sendLive2DConfig() {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.log('无法发送Live2D配置：未连接到服务器');
            return;
        }
        
        const configMessage = {
            type: 'live2d_config',
            enabled: this.settings.live2dEnabled
        };
        
        this.websocket.send(JSON.stringify(configMessage));
        this.log('发送Live2D配置:', configMessage);
    }
    
    // 查询Live2D状态
    queryLive2DStatus() {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            return;
        }
        
        const statusMessage = {
            type: 'live2d_status'
        };
        
        this.websocket.send(JSON.stringify(statusMessage));
    }
    
    // 更新Live2D状态显示
    updateLive2DStatusDisplay() {
        const live2dStatus = document.getElementById('live2d-status');
        if (live2dStatus) {
            live2dStatus.textContent = this.settings.live2dEnabled ? '已启用' : '已禁用';
            live2dStatus.style.color = this.settings.live2dEnabled ? '#48bb78' : '#e53e3e';
        }
    }
    
    // 切换Live2D显示
    toggleLive2DDisplay(enable) {
        if (enable) {
            // 启用Live2D
            if (!this.model) {
                this.loadLive2DModel(this.settings.currentModel || 'openSource');
            }
            const canvasContainer = document.getElementById('canvas-container');
            if (canvasContainer) {
                canvasContainer.style.display = 'block';
            }
            this.log('✅ Live2D显示已启用');
        } else {
            // 禁用Live2D
            if (this.model) {
                this.app.stage.removeChild(this.model);
                this.model = null;
            }
            const canvasContainer = document.getElementById('canvas-container');
            if (canvasContainer) {
                canvasContainer.style.display = 'none';
            }
            this.log('✅ Live2D显示已禁用');
        }
    }
    
    // 发送TTS配置到服务器
    sendTTSConfig() {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.showTTSFeedback('无法发送TTS配置：未连接到服务器', 'error');
            return;
        }
        
        const configMessage = {
            type: 'tts_config',
            enabled: this.settings.ttsEnabled,
            model: this.settings.ttsModel
        };
        
        this.websocket.send(JSON.stringify(configMessage));
        this.log('发送TTS配置:', configMessage);
    }
    
    // 查询TTS状态
    queryTTSStatus() {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            return;
        }
        
        const statusMessage = {
            type: 'tts_status'
        };
        
        this.websocket.send(JSON.stringify(statusMessage));
    }
    
    // 测试TTS功能
    testTTS() {
        const testButton = document.getElementById('test-tts');
        if (!testButton) return;
        
        if (!this.settings.ttsEnabled) {
            this.showTTSFeedback('请先启用TTS功能', 'error');
            return;
        }
        
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.showTTSFeedback('无法测试：未连接到服务器', 'error');
            return;
        }
        
        // 禁用按钮，显示测试中
        testButton.disabled = true;
        testButton.textContent = '测试中...';
        this.showTTSFeedback('正在测试TTS...', 'info');
        
        // 发送测试文本（通过process_input_stream）
        const testMessage = {
            type: 'text',
            content: '你好，我是女娲，这是TTS语音测试。'
        };
        
        this.websocket.send(JSON.stringify(testMessage));
        
        // 3秒后恢复按钮
        setTimeout(() => {
            testButton.disabled = false;
            testButton.textContent = '测试TTS';
        }, 3000);
    }
    
    // 更新TTS状态显示
    updateTTSStatusDisplay() {
        const ttsStatusDisplay = document.getElementById('tts-status-display');
        const ttsStatusText = document.getElementById('tts-status-text');
        
        if (!ttsStatusDisplay || !ttsStatusText) return;
        
        if (this.settings.ttsEnabled) {
            ttsStatusDisplay.style.display = 'flex';
            ttsStatusDisplay.classList.add('active');
            ttsStatusText.textContent = `TTS: ${this.settings.ttsModel.split('/').pop()}`;
        } else {
            ttsStatusDisplay.style.display = 'none';
            ttsStatusDisplay.classList.remove('active');
        }
    }
    
    // 显示TTS反馈信息
    showTTSFeedback(message, type = 'info') {
        const ttsFeedback = document.getElementById('tts-feedback');
        if (!ttsFeedback) return;
        
        ttsFeedback.textContent = message;
        ttsFeedback.className = type; // success, error, info
        
        // 5秒后清除
        setTimeout(() => {
            if (ttsFeedback.textContent === message) {
                ttsFeedback.textContent = '';
                ttsFeedback.className = '';
            }
        }, 5000);
    }
    
    // 处理TTS音频数据
    handleTTSAudio(audioData, text) {
        if (!audioData) {
            this.showTTSFeedback('收到空的音频数据', 'error');
            return;
        }
        
        // 创建音频上下文播放
        try {
            // 将base64转换为Blob
            const byteCharacters = atob(audioData);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const audioBlob = new Blob([byteArray], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // 创建并播放音频
            const audio = new Audio(audioUrl);
            audio.volume = this.settings.volume / 100;
            
            audio.onplay = () => {
                this.showTTSFeedback(`正在播放: ${text || '语音'}`, 'success');
                this.log('TTS音频开始播放');
            };
            
            audio.onended = () => {
                this.log('TTS音频播放完成');
                URL.revokeObjectURL(audioUrl); // 释放内存
            };
            
            audio.onerror = (e) => {
                this.showTTSFeedback('音频播放失败', 'error');
                this.log('TTS音频播放错误:', e);
            };
            
            audio.play();
            
        } catch (error) {
            this.showTTSFeedback('音频处理失败: ' + error.message, 'error');
            this.log('TTS音频处理错误:', error);
        }
    }
    
    // 初始化Electron特有设置
    initElectronSettings() {
        if (!this.isElectron) return;
        
        // 添加electron类到body
        document.body.classList.add('electron');
        
        // 加载并初始化Electron特有设置
        this.loadElectronSettings();
        
        // 窗口置顶设置
        const alwaysOnTopCheckbox = document.getElementById('always-on-top');
        alwaysOnTopCheckbox.addEventListener('change', (event) => {
            this.ipcRenderer.send('toggle-always-on-top', event.target.checked);
        });
        
        // 鼠标穿透设置
        const mouseThroughCheckbox = document.getElementById('mouse-through');
        mouseThroughCheckbox.addEventListener('change', (event) => {
            this.ipcRenderer.send('set-ignore-mouse-events', event.target.checked, { forward: true });
        });
        
        // 显示在任务栏设置
        const showTaskbarCheckbox = document.getElementById('show-taskbar');
        showTaskbarCheckbox.addEventListener('change', (event) => {
            // 显示在任务栏的设置在Electron主进程中处理，这里可以添加相应的逻辑
            this.log('显示在任务栏设置已更新:', event.target.checked);
        });
    }
    
    // 加载Electron特有设置
    loadElectronSettings() {
        if (!this.isElectron) return;
        
        // 优先从settings对象读取，如果不存在则从localStorage读取（向后兼容）
        let alwaysOnTop = true;
        let mouseThrough = false;
        let showTaskbar = true;
        let windowWidth = 800;
        let windowHeight = 600;
        
        // 从settings读取
        if (this.settings.alwaysOnTop !== undefined) alwaysOnTop = this.settings.alwaysOnTop;
        if (this.settings.mouseThrough !== undefined) mouseThrough = this.settings.mouseThrough;
        if (this.settings.showTaskbar !== undefined) showTaskbar = this.settings.showTaskbar;
        if (this.settings.windowWidth !== undefined) windowWidth = this.settings.windowWidth;
        if (this.settings.windowHeight !== undefined) windowHeight = this.settings.windowHeight;
        
        // 如果settings中没有，尝试从localStorage读取（向后兼容）
        if (!this.settings.hasOwnProperty('alwaysOnTop')) {
            const savedAlwaysOnTop = localStorage.getItem('nuwa_always_on_top');
            if (savedAlwaysOnTop !== null) alwaysOnTop = savedAlwaysOnTop === 'true';
        }
        if (!this.settings.hasOwnProperty('mouseThrough')) {
            const savedMouseThrough = localStorage.getItem('nuwa_mouse_through');
            if (savedMouseThrough !== null) mouseThrough = savedMouseThrough === 'true';
        }
        if (!this.settings.hasOwnProperty('showTaskbar')) {
            const savedShowTaskbar = localStorage.getItem('nuwa_show_taskbar');
            if (savedShowTaskbar !== null) showTaskbar = savedShowTaskbar === 'true';
        }
        
        // 窗口置顶设置
        const alwaysOnTopCheckbox = document.getElementById('always-on-top');
        if (alwaysOnTopCheckbox) {
            alwaysOnTopCheckbox.checked = alwaysOnTop;
            this.ipcRenderer.send('toggle-always-on-top', alwaysOnTop);
            this.log('窗口置顶设置已初始化:', alwaysOnTop);
        }
        
        // 鼠标穿透设置
        const mouseThroughCheckbox = document.getElementById('mouse-through');
        if (mouseThroughCheckbox) {
            mouseThroughCheckbox.checked = mouseThrough;
            this.ipcRenderer.send('set-ignore-mouse-events', mouseThrough, { forward: true });
            this.log('鼠标穿透设置已初始化:', mouseThrough);
        }
        
        // 显示在任务栏设置
        const showTaskbarCheckbox = document.getElementById('show-taskbar');
        if (showTaskbarCheckbox) {
            showTaskbarCheckbox.checked = showTaskbar;
            this.log('显示在任务栏设置已初始化:', showTaskbar);
        }
        
        // 窗口大小设置
        const windowWidthSlider = document.getElementById('window-width');
        const windowHeightSlider = document.getElementById('window-height');
        const widthValue = document.getElementById('width-value');
        const heightValue = document.getElementById('height-value');
        
        if (windowWidthSlider && widthValue) {
            windowWidthSlider.value = windowWidth;
            widthValue.textContent = windowWidth;
        }
        if (windowHeightSlider && heightValue) {
            windowHeightSlider.value = windowHeight;
            heightValue.textContent = windowHeight;
        }
        
        // 如果窗口大小已设置，发送到主进程
        if (windowWidth && windowHeight && this.ipcRenderer) {
            this.ipcRenderer.send('resize-window', windowWidth, windowHeight);
        }
    }
    
    // 切换设置菜单
    toggleSettingsMenu() {
        const menu = document.getElementById('settings-menu');
        this.isMenuOpen = !this.isMenuOpen;
        
        if (this.isMenuOpen) {
            menu.style.display = 'flex';
        } else {
            menu.style.display = 'none';
        }
    }
    
    // 加载设置
    loadSettings() {
        try {
            // 尝试新格式
            let savedSettings = localStorage.getItem('nuwaSettings');
            
            // 如果新格式不存在，尝试旧格式（向后兼容）
            if (!savedSettings) {
                savedSettings = localStorage.getItem('nuwa_settings');
                if (savedSettings) {
                    this.log('检测到旧格式设置，将迁移到新格式');
                }
            }
            
            if (savedSettings) {
                const parsed = JSON.parse(savedSettings);
                // 合并保存的设置
                Object.assign(this.settings, parsed);
                this.log('已加载保存的设置:', this.settings);
                
                // 如果有API配置，更新显示
                if (this.settings.apiConfigs && this.settings.apiConfigs.length > 0) {
                    setTimeout(() => {
                        const configSelect = document.getElementById('api-config-select');
                        if (configSelect) {
                            this.loadAPIConfigList();
                        }
                        this.updateCurrentAPIName(this.settings.currentApiConfig);
                    }, 100);
                }
            }
        } catch (error) {
            this.log('⚠️ 加载设置失败:', error.message);
        }
    }
    
    // 保存设置
    saveSettings() {
        // 获取设置值
        const backendUrl = document.getElementById('backend-url').value;
        const modelScale = parseFloat(document.getElementById('model-scale').value);
        const volume = parseInt(document.getElementById('volume').value);
        const debugMode = document.getElementById('debug-mode').checked;
        const currentModel = document.getElementById('model-select').value;
        
        // 更新设置
        this.settings.backendUrl = backendUrl;
        this.settings.modelScale = modelScale;
        this.settings.volume = volume;
        this.settings.debugMode = debugMode;
        this.settings.currentModel = currentModel;
        
        // 保存Electron特有设置
        if (this.isElectron) {
            const alwaysOnTop = document.getElementById('always-on-top').checked;
            const mouseThrough = document.getElementById('mouse-through').checked;
            const showTaskbar = document.getElementById('show-taskbar').checked;
            
            // 保存窗口大小
            const windowWidth = document.getElementById('window-width');
            const windowHeight = document.getElementById('window-height');
            if (windowWidth && windowHeight) {
                this.settings.windowWidth = parseInt(windowWidth.value);
                this.settings.windowHeight = parseInt(windowHeight.value);
            }
            
            // 保存到设置对象
            this.settings.alwaysOnTop = alwaysOnTop;
            this.settings.mouseThrough = mouseThrough;
            this.settings.showTaskbar = showTaskbar;
            
            // 发送到主进程
            this.ipcRenderer.send('toggle-always-on-top', alwaysOnTop);
            this.ipcRenderer.send('set-ignore-mouse-events', mouseThrough, { forward: true });
            this.log('Electron特有设置已更新');
        }
        
        // 使用统一的保存方法
        this.saveSettingsToStorage();
        
        // 保存表情配置
        this.saveExpressionConfigs();
        
        // 如果模型已更改，重新加载模型
        const previousModel = this.settings.currentModel;
        if (currentModel !== previousModel) {
            this.log(`模型已更改: ${previousModel} -> ${currentModel}`);
            this.switchModel(currentModel);
        }
        
        // 更新模型缩放（如果模型已加载）
        if (this.model) {
            const previousScale = this.settings.modelScale;
            if (modelScale !== previousScale) {
                this.log(`模型缩放已更改: ${previousScale} -> ${modelScale}`);
                this.model.scale.set(modelScale);
                this.centerModel();
            }
        }
        
        // 重新连接WebSocket
        if (this.websocket) {
            this.websocket.close();
        }
        this.initWebSocket();
        
        // 更新UI
        this.toggleDebugLogs();
        this.toggleSettingsMenu();
        
        this.log('设置已保存');
    }
    
    // 切换调试日志显示
    toggleDebugLogs() {
        const logs = document.getElementById('debug-logs');
        if (this.settings.debugMode) {
            logs.style.display = 'block';
        } else {
            logs.style.display = 'none';
        }
    }
    
    // 初始化控制按钮
    initControlButtons() {
        this.log('初始化控制按钮');
        
        // 设置按钮
        this.settingsBtn = document.getElementById('settings-btn');
        if (this.settingsBtn) {
            this.log('找到settings-btn元素');
            this.settingsBtn.addEventListener('click', () => {
                this.log('点击了设置按钮');
                this.toggleSettingsMenu();
            });
        } else {
            this.log('未找到settings-btn元素');
        }
        
        // 面板按钮
        this.panelBtn = document.getElementById('panel-btn');
        if (this.panelBtn) {
            this.log('找到panel-btn元素');
            this.panelBtn.addEventListener('click', () => {
                this.log('点击了面板按钮');
                this.toggleBioMonitor();
            });
        } else {
            this.log('未找到panel-btn元素');
        }
        
        // 锁定/解锁按钮
        this.lockBtn = document.getElementById('lock-btn');
        if (this.lockBtn) {
            this.log('找到lock-btn元素');
            this.lockBtn.addEventListener('click', () => {
                this.log('点击了锁定/解锁按钮');
                this.toggleMouseThrough();
            });
            
            // 初始化按钮状态 - 默认解锁状态
            this.log('初始化锁定/解锁按钮状态为解锁');
            this.lockBtn.classList.remove('locked');
            this.lockBtn.title = '锁定';
            this.lockBtn.innerHTML = '<span class="control-icon">🔒</span>';
            this.log('锁定/解锁按钮初始状态设置完成');
        } else {
            this.log('未找到lock-btn元素');
        }
        
        // 初始化生物监控面板状态
        this.isBioMonitorVisible = true;
        this.log('初始化生物监控面板状态为可见');
    }
    
    // 切换生物监控面板显示/隐藏
    toggleBioMonitor() {
        this.log('切换生物监控面板显示/隐藏');
        const bioMonitor = document.getElementById('bio-monitor');
        if (!bioMonitor) {
            this.log('未找到bio-monitor元素');
            return;
        }
        
        this.isBioMonitorVisible = !this.isBioMonitorVisible;
        this.log('生物监控面板当前状态:', this.isBioMonitorVisible);
        
        if (this.isBioMonitorVisible) {
            bioMonitor.style.display = 'block';
            this.panelBtn.title = '隐藏面板';
            this.log('显示生物监控面板');
        } else {
            bioMonitor.style.display = 'none';
            this.panelBtn.title = '显示面板';
            this.log('隐藏生物监控面板');
        }
    }
    
    // 切换鼠标穿透
    toggleMouseThrough() {
        const isLocked = this.lockBtn.classList.contains('locked');
        this.log('切换鼠标穿透状态，当前锁定状态:', isLocked);
        const cancelProtection = () => {
            if (this.mouseThroughHandler) {
                document.removeEventListener('mousemove', this.mouseThroughHandler);
                this.mouseThroughHandler = null;
            }
            if (this.isElectron) {
                this.ipcRenderer.send('set-ignore-mouse-events', false);
            }
        };
        
        if (isLocked) {
            // 解锁：允许点击其他按钮和拖动窗口
            this.log('执行解锁操作');
            this.lockBtn.classList.remove('locked');
            this.lockBtn.title = '锁定';
            this.lockBtn.innerHTML = '<span class="control-icon">🔒</span>';
            this.log('更新锁定/解锁按钮状态为解锁');
            
            cancelProtection();
        } else {
            // 锁定：启用鼠标穿透，但控制按钮仍可点击
            this.log('执行锁定操作');
            this.lockBtn.classList.add('locked');
            this.lockBtn.title = '解锁';
            this.lockBtn.innerHTML = '<span class="control-icon">🔓</span>';
            this.log('更新锁定/解锁按钮状态为锁定');
            
            // 启用鼠标穿透，同时确保控制按钮可点击
            if (this.isElectron) {
                this.log('启用鼠标穿透，但确保控制按钮可点击');
                
                // 立即启用鼠标穿透，不等待鼠标移动
                this.ipcRenderer.send('set-ignore-mouse-events', true, { forward: true });
                
                // 注册鼠标移动事件，检测鼠标是否在控制按钮/聊天按钮/面板/输入栏上
                this.setupMouseThroughWithButtonProtection();
            } else {
                this.log('非Electron环境，无法启用鼠标穿透');
            }
        }
    }
    
    // 设置鼠标穿透，同时保护控制按钮可点击
    setupMouseThroughWithButtonProtection() {
        if (!this.isElectron) return;
        
        this.log('设置鼠标穿透保护，确保控制按钮可点击');
        
        const hotspots = [
            '.control-btn',
            '.chat-trigger',
            '.floating-input',
            '.settings-menu',
            '.bio-monitor',
            '.debug-logs'
        ];
        
        // 监听鼠标移动事件
        this.mouseThroughHandler = (event) => {
            const targets = document.querySelectorAll(hotspots.join(','));
            let isOverButton = false;
            targets.forEach(target => {
                const rect = target.getBoundingClientRect();
                if (event.clientX >= rect.left && event.clientX <= rect.right &&
                    event.clientY >= rect.top && event.clientY <= rect.bottom) {
                    isOverButton = true;
                }
            });
            
            // 如果鼠标在可交互区域，关闭穿透，否则开启穿透
            this.ipcRenderer.send('set-ignore-mouse-events', !isOverButton, { forward: true });
        };
        
        // 添加事件监听器
        document.addEventListener('mousemove', this.mouseThroughHandler);
        this.log('添加了鼠标移动事件监听器，用于保护按钮和面板可点击');
    }
    
    // 初始化事件监听器
    initEventListeners() {
        // 防止默认右键菜单
        document.addEventListener('contextmenu', (event) => {
            // 只有在模型上的右键点击才允许默认行为
            if (!this.isMenuOpen) {
                event.preventDefault();
            }
        });
        
        // 点击页面关闭设置菜单
        document.addEventListener('click', (event) => {
            // 检查点击是否在控制按钮、聊天按钮或设置菜单上
            const isControlButton = event.target.closest('.control-btn');
            const isChatButton = event.target.closest('.chat-trigger');
            const isSettingsMenu = event.target.closest('#settings-menu');
            const isExpressionButton = event.target.closest('.expression-btn');
            
            // 如果点击在这些元素上，不关闭设置菜单
            if (isControlButton || isChatButton || isSettingsMenu || isExpressionButton) {
                return;
            }
            
            // 如果设置菜单是打开的，且点击在外面，则关闭
            if (this.isMenuOpen) {
                const menu = document.getElementById('settings-menu');
                if (menu && !menu.contains(event.target)) {
                    this.toggleSettingsMenu();
                }
            }
        }, true); // 使用捕获阶段，确保优先处理
        
        // 添加全局鼠标事件监听器，确保所有控制按钮始终可点击
        if (this.isElectron) {
            document.addEventListener('mousemove', (event) => {
                // 检查鼠标是否在控制按钮或聊天按钮上
                const allButtons = document.querySelectorAll('.control-btn, .chat-trigger, #floating-input, #settings-menu');
                let isOverButton = false;
                
                allButtons.forEach(button => {
                    const rect = button.getBoundingClientRect();
                    if (event.clientX >= rect.left && event.clientX <= rect.right &&
                        event.clientY >= rect.top && event.clientY <= rect.bottom) {
                        isOverButton = true;
                    }
                });
                
                // 只有当鼠标不在任何按钮上且锁定状态时，才启用鼠标穿透
                const isLocked = this.lockBtn && this.lockBtn.classList.contains('locked');
                if (isLocked) {
                    this.ipcRenderer.send('set-ignore-mouse-events', !isOverButton, { forward: true });
                }
            });
        }
    }
    
    // 日志记录
    log(...args) {
        console.log('[Nuwa]', ...args);
        
        // 如果调试模式开启，显示在调试面板
        if (this.settings.debugMode) {
            const logs = document.getElementById('debug-logs');
            const logEntry = document.createElement('div');
            logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${args.map(arg => 
                typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
            ).join(' ')}`;
            logs.appendChild(logEntry);
            logs.scrollTop = logs.scrollHeight;
        }
    }
    
    // 显示错误消息
    showError(message) {
        Swal.fire({
            title: '错误',
            text: message,
            icon: 'error',
            confirmButtonText: '确定'
        });
    }
    
    // 显示成功消息
    showSuccess(message) {
        Swal.fire({
            title: '成功',
            text: message,
            icon: 'success',
            confirmButtonText: '确定'
        });
    }
    
    // ==================== API配置管理 ====================
    
    // 初始化API配置管理器
    initAPIConfigManager() {
        const configSelect = document.getElementById('api-config-select');
        const addBtn = document.getElementById('add-api-config');
        const deleteBtn = document.getElementById('delete-api-config');
        const editBtn = document.getElementById('edit-api-config');
        const saveBtn = document.getElementById('save-api-config');
        const cancelBtn = document.getElementById('cancel-api-edit');
        const applyBtn = document.getElementById('apply-api-config');
        const testBtn = document.getElementById('test-api-connection');
        
        if (!configSelect || !addBtn || !deleteBtn || !editBtn) return;
        
        // 加载API配置列表
        this.loadAPIConfigList();
        
        // 绑定事件
        addBtn.addEventListener('click', () => this.showAPIConfigEditor('add'));
        editBtn.addEventListener('click', () => this.showAPIConfigEditor('edit'));
        deleteBtn.addEventListener('click', () => this.deleteAPIConfig());
        saveBtn.addEventListener('click', () => this.saveAPIConfig());
        cancelBtn.addEventListener('click', () => this.hideAPIConfigEditor());
        applyBtn.addEventListener('click', () => this.applyAPIConfig());
        if (testBtn) {
            testBtn.addEventListener('click', () => this.testAPIConnection());
        }
        
        // 配置选择变化
        configSelect.addEventListener('change', (e) => {
            const index = e.target.value;
            if (index === '') {
                this.hideAPIConfigEditor();
                this.updateCurrentAPIName(null);
            } else {
                this.updateCurrentAPIName(parseInt(index));
            }
        });
    }
    
    // 加载API配置列表
    loadAPIConfigList() {
        const configSelect = document.getElementById('api-config-select');
        if (!configSelect) return;
        
        // 清空现有选项（保留第一个）
        configSelect.innerHTML = '<option value="">-- 选择配置 --</option>';
        
        // 加载配置
        const configs = this.settings.apiConfigs || [];
        
        // 如果没有配置，创建默认配置
        if (configs.length === 0) {
            const defaultConfig = {
                name: '本地LM Studio',
                wsUrl: 'ws://127.0.0.1:8766',
                llmUrl: 'http://127.0.0.1:1234/v1',
                apiKey: 'lm-studio',
                model: 'local-model',
                description: '默认本地配置'
            };
            configs.push(defaultConfig);
            this.settings.apiConfigs = configs;
            this.saveSettingsToStorage();
        }
        
        // 添加配置选项
        configs.forEach((config, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = `${config.name} - ${config.wsUrl}`;
            configSelect.appendChild(option);
        });
        
        // 设置当前选择
        if (this.settings.currentApiConfig !== null && this.settings.currentApiConfig < configs.length) {
            configSelect.value = this.settings.currentApiConfig;
            this.updateCurrentAPIName(this.settings.currentApiConfig);
        }
    }
    
    // 显示API配置编辑器
    showAPIConfigEditor(mode) {
        const detailsDiv = document.getElementById('api-config-details');
        const configSelect = document.getElementById('api-config-select');
        
        if (!detailsDiv || !configSelect) return;
        
        detailsDiv.style.display = 'block';
        
        if (mode === 'add') {
            // 清空表单
            document.getElementById('api-name').value = '';
            document.getElementById('api-ws-url').value = 'ws://127.0.0.1:8766';
            document.getElementById('api-llm-url').value = 'http://127.0.0.1:1234/v1';
            document.getElementById('api-key').value = 'lm-studio';
            document.getElementById('api-model').value = 'local-model';
            document.getElementById('api-description').value = '';
        } else if (mode === 'edit') {
            // 编辑模式需要选中配置
            const selectedIndex = configSelect.value;
            if (selectedIndex === '') {
                this.showError('请先选择一个配置');
                detailsDiv.style.display = 'none';
                return;
            }
            
            const config = this.settings.apiConfigs[parseInt(selectedIndex)];
            if (config) {
                document.getElementById('api-name').value = config.name || '';
                document.getElementById('api-ws-url').value = config.wsUrl || '';
                document.getElementById('api-llm-url').value = config.llmUrl || '';
                document.getElementById('api-key').value = config.apiKey || '';
                document.getElementById('api-model').value = config.model || '';
                document.getElementById('api-description').value = config.description || '';
            }
        }
    }
    
    // 隐藏API配置编辑器
    hideAPIConfigEditor() {
        const detailsDiv = document.getElementById('api-config-details');
        if (detailsDiv) {
            detailsDiv.style.display = 'none';
        }
    }
    
    // 保存API配置
    saveAPIConfig() {
        const name = document.getElementById('api-name').value.trim();
        const wsUrl = document.getElementById('api-ws-url').value.trim();
        const llmUrl = document.getElementById('api-llm-url').value.trim();
        const apiKey = document.getElementById('api-key').value.trim();
        const model = document.getElementById('api-model').value.trim();
        const description = document.getElementById('api-description').value.trim();
        
        if (!name || !wsUrl) {
            this.showError('配置名称和WebSocket地址为必填项');
            return;
        }
        
        const config = {
            name,
            wsUrl,
            llmUrl,
            apiKey,
            model,
            description
        };
        
        const configSelect = document.getElementById('api-config-select');
        const selectedIndex = configSelect.value;
        
        if (selectedIndex === '') {
            // 添加新配置
            this.settings.apiConfigs.push(config);
            this.log('✅ 新API配置已添加:', name);
        } else {
            // 更新现有配置
            const index = parseInt(selectedIndex);
            this.settings.apiConfigs[index] = config;
            this.log('✅ API配置已更新:', name);
        }
        
        // 保存到存储
        this.saveSettingsToStorage();
        
        // 重新加载列表
        this.loadAPIConfigList();
        
        // 隐藏编辑器
        this.hideAPIConfigEditor();
        
        // 显示成功消息
        this.showSuccess(`API配置 "${name}" 已保存`);
    }
    
    // 删除API配置
    deleteAPIConfig() {
        const configSelect = document.getElementById('api-config-select');
        const selectedIndex = configSelect.value;
        
        if (selectedIndex === '') {
            this.showError('请先选择一个配置');
            return;
        }
        
        const index = parseInt(selectedIndex);
        const config = this.settings.apiConfigs[index];
        
        Swal.fire({
            title: '确认删除',
            text: `确定要删除配置 "${config.name}" 吗？`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: '删除',
            cancelButtonText: '取消'
        }).then((result) => {
            if (result.isConfirmed) {
                this.settings.apiConfigs.splice(index, 1);
                
                // 如果删除的是当前使用的配置，重置当前配置
                if (this.settings.currentApiConfig === index) {
                    this.settings.currentApiConfig = null;
                } else if (this.settings.currentApiConfig > index) {
                    this.settings.currentApiConfig--;
                }
                
                this.saveSettingsToStorage();
                this.loadAPIConfigList();
                this.hideAPIConfigEditor();
                this.updateCurrentAPIName(null);
                this.showSuccess(`配置 "${config.name}" 已删除`);
            }
        });
    }
    
    // 应用API配置
    applyAPIConfig() {
        const configSelect = document.getElementById('api-config-select');
        const selectedIndex = configSelect.value;
        
        if (selectedIndex === '') {
            this.showError('请先选择一个配置');
            return;
        }
        
        const index = parseInt(selectedIndex);
        const config = this.settings.apiConfigs[index];
        
        if (!config) {
            this.showError('配置不存在');
            return;
        }
        
        // 更新当前配置
        this.settings.currentApiConfig = index;
        
        // 更新WebSocket地址
        this.settings.backendUrl = config.wsUrl;
        const backendUrlInput = document.getElementById('backend-url');
        if (backendUrlInput) {
            backendUrlInput.value = config.wsUrl;
        }
        
        // 保存设置
        this.saveSettingsToStorage();
        
        // 更新当前配置显示
        this.updateCurrentAPIName(index);
        
        // 重新连接WebSocket
        if (this.websocket) {
            try {
                this.websocket.close();
            } catch (e) {
                // 忽略关闭错误
            }
        }
        
        // 延迟重连，让UI先更新
        setTimeout(() => {
            this.initWebSocket();
            this.showSuccess(`已应用配置: ${config.name}\nWebSocket: ${config.wsUrl}`);
        }, 500);
    }
    
    // 更新当前API名称显示
    updateCurrentAPIName(index) {
        const currentNameSpan = document.getElementById('current-api-name');
        if (!currentNameSpan) return;
        
        if (index === null || index === undefined) {
            currentNameSpan.textContent = '未选择';
            currentNameSpan.style.color = '#e53e3e';
        } else {
            const config = this.settings.apiConfigs[index];
            if (config) {
                currentNameSpan.textContent = config.name;
                currentNameSpan.style.color = '#48bb78';
            } else {
                currentNameSpan.textContent = '未知';
                currentNameSpan.style.color = '#e53e3e';
            }
        }
    }
    
    // 测试API连接
    testAPIConnection() {
        const wsUrl = document.getElementById('api-ws-url').value.trim();
        const llmUrl = document.getElementById('api-llm-url').value.trim();
        const apiKey = document.getElementById('api-key').value.trim();
        const model = document.getElementById('api-model').value.trim();
        const resultDiv = document.getElementById('connection-test-result');
        
        if (!wsUrl) {
            this.showConnectionResult('❌ WebSocket地址不能为空', 'error');
            return;
        }
        
        if (!wsUrl.startsWith('ws://') && !wsUrl.startsWith('wss://')) {
            this.showConnectionResult('❌ WebSocket地址必须以 ws:// 或 wss:// 开头', 'error');
            return;
        }
        
        this.showConnectionResult('🔄 正在测试连接...', 'testing');
        
        // 测试WebSocket连接
        const testSocket = new WebSocket(wsUrl);
        let testTimeout;
        
        // 设置超时
        const timeoutPromise = new Promise((_, reject) => {
            testTimeout = setTimeout(() => {
                reject(new Error('连接超时'));
            }, 5000); // 5秒超时
        });
        
        // WebSocket连接测试
        const socketPromise = new Promise((resolve, reject) => {
            testSocket.onopen = () => {
                clearTimeout(testTimeout);
                resolve('WebSocket连接成功');
                testSocket.close();
            };
            
            testSocket.onerror = (error) => {
                clearTimeout(testTimeout);
                reject(new Error('WebSocket连接失败'));
            };
            
            testSocket.onclose = (event) => {
                if (event.code !== 1000) { // 1000是正常关闭
                    clearTimeout(testTimeout);
                    reject(new Error(`WebSocket异常关闭: ${event.code}`));
                }
            };
        });
        
        // 并发测试WebSocket和超时
        Promise.race([socketPromise, timeoutPromise])
            .then((wsResult) => {
                // WebSocket成功，继续测试LLM API（如果有）
                if (llmUrl) {
                    return this.testLLMAPI(llmUrl, apiKey, model);
                } else {
                    return Promise.resolve(wsResult);
                }
            })
            .then((result) => {
                this.showConnectionResult(`✅ ${result}`, 'success');
            })
            .catch((error) => {
                this.showConnectionResult(`❌ ${error.message}`, 'error');
            });
    }
    
    // 测试LLM API连接
    async testLLMAPI(llmUrl, apiKey, model) {
        try {
            // 构建测试请求
            const testUrl = llmUrl.replace(/\/+$/, '') + '/models';
            
            const headers = {
                'Content-Type': 'application/json'
            };
            
            if (apiKey && apiKey !== 'lm-studio') {
                headers['Authorization'] = `Bearer ${apiKey}`;
            }
            
            // 使用fetch测试API
            const response = await fetch(testUrl, {
                method: 'GET',
                headers: headers,
                mode: 'cors'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // 检查模型是否存在（如果指定了模型）
            if (model && data.data) {
                const found = data.data.find(m => 
                    m.id === model || 
                    m.name === model || 
                    (m.model && m.model === model)
                );
                
                if (!found) {
                    return `LLM API连接成功，但未找到模型 "${model}"`;
                }
            }
            
            return 'LLM API连接成功';
        } catch (error) {
            throw new Error(`LLM API测试失败: ${error.message}`);
        }
    }
    
    // 显示连接测试结果
    showConnectionResult(message, type) {
        const resultDiv = document.getElementById('connection-test-result');
        if (!resultDiv) return;
        
        resultDiv.style.display = 'block';
        resultDiv.textContent = message;
        
        // 根据类型设置样式
        if (type === 'success') {
            resultDiv.style.background = 'rgba(72, 187, 120, 0.3)';
            resultDiv.style.border = '1px solid #48bb78';
            resultDiv.style.color = '#48bb78';
        } else if (type === 'error') {
            resultDiv.style.background = 'rgba(229, 62, 62, 0.3)';
            resultDiv.style.border = '1px solid #e53e3e';
            resultDiv.style.color = '#e53e3e';
        } else if (type === 'testing') {
            resultDiv.style.background = 'rgba(66, 153, 225, 0.3)';
            resultDiv.style.border = '1px solid #4299e1';
            resultDiv.style.color = '#4299e1';
        }
        
        // 3秒后自动隐藏成功消息
        if (type === 'success') {
            setTimeout(() => {
                resultDiv.style.display = 'none';
            }, 3000);
        }
    }
    
    // 保存设置到本地存储
    saveSettingsToStorage() {
        try {
            localStorage.setItem('nuwaSettings', JSON.stringify(this.settings));
            this.log('💾 设置已保存到本地存储');
        } catch (e) {
            this.log('❌ 保存设置失败:', e);
        }
    }
    
    // ==================== 启动管理器相关方法 ====================
    
    // 检查WebSocket连接状态
    async checkConnectionStatus() {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        if (!statusDot || !statusText) return;
        
        try {
            // 尝试创建临时WebSocket连接测试
            const ws = new WebSocket(this.settings.backendUrl);
            
            statusDot.className = 'status-dot connecting';
            statusText.textContent = '连接中...';
            
            return new Promise((resolve) => {
                let resolved = false;
                
                ws.onopen = () => {
                    if (!resolved) {
                        resolved = true;
                        ws.close();
                        statusDot.className = 'status-dot connected';
                        statusText.textContent = '已连接';
                        this.log('✅ WebSocket连接正常');
                        resolve(true);
                    }
                };
                
                ws.onerror = () => {
                    if (!resolved) {
                        resolved = true;
                        statusDot.className = 'status-dot';
                        statusText.textContent = '未连接';
                        this.log('❌ WebSocket连接失败');
                        resolve(false);
                    }
                };
                
                ws.onclose = () => {
                    if (!resolved) {
                        resolved = true;
                        statusDot.className = 'status-dot';
                        statusText.textContent = '未连接';
                        resolve(false);
                    }
                };
                
                setTimeout(() => {
                    if (!resolved) {
                        resolved = true;
                        ws.close();
                        statusDot.className = 'status-dot';
                        statusText.textContent = '连接超时';
                        this.log('⚠️ WebSocket连接超时');
                        resolve(false);
                    }
                }, 3000);
            });
        } catch (e) {
            statusDot.className = 'status-dot';
            statusText.textContent = '错误';
            this.log('❌ 检查连接时出错:', e);
            return false;
        }
    }
    
    // 显示服务器未启动警告
    showServerWarning() {
        // 检查是否已经存在警告
        if (document.getElementById('serverWarning')) return;
        
        const warning = document.createElement('div');
        warning.id = 'serverWarning';
        warning.className = 'server-warning';
        warning.innerHTML = `
            <h3>⚠️ WebSocket服务器未启动</h3>
            <p>请先启动WebSocket服务器才能正常通信</p>
            <p style="font-size: 12px; margin-top: 10px; opacity: 0.8;">
                命令: python server_async.py
            </p>
            <button onclick="this.parentElement.remove()">知道了</button>
            <button onclick="window.open('启动管理器.html', '_blank')" style="background: #48bb78; margin-left: 10px;">
                打开启动管理器
            </button>
        `;
        document.body.appendChild(warning);
        
        // 5秒后自动隐藏
        setTimeout(() => {
            if (warning.parentElement) {
                warning.remove();
            }
        }, 8000);
    }
    
    // 定期检查连接状态
    startConnectionMonitor() {
        setInterval(async () => {
            await this.checkConnectionStatus();
        }, 10000); // 每10秒检查一次
    }
    
    // 尝试自动连接
    async autoConnect() {
        this.log('🔄 尝试自动连接WebSocket服务器...');
        
        const connected = await this.checkConnectionStatus();
        
        if (!connected) {
            this.log('❌ 自动连接失败，显示警告');
            this.showServerWarning();
            return false;
        }
        
        // 如果已连接，重新初始化WebSocket
        if (this.websocket) {
            try {
                this.websocket.close();
            } catch (e) {
                // 忽略关闭错误
            }
        }
        
        this.initWebSocket();
        return true;
    }
    
    // 显示快速连接提示
    showQuickConnectTip() {
        const tip = document.createElement('div');
        tip.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(102, 126, 234, 0.95);
            color: white;
            padding: 15px 25px;
            border-radius: 10px;
            z-index: 9998;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
            font-size: 14px;
            text-align: center;
        `;
        
        tip.innerHTML = `
            <div style="margin-bottom: 8px;">💡 快速连接提示</div>
            <div style="font-size: 12px; opacity: 0.9;">
                1. 点击左上角 🚀 启动管理器<br>
                2. 选择 "WebSocket 服务器模式"<br>
                3. 然后点击 "打开浏览器"
            </div>
            <button onclick="this.parentElement.remove()" style="
                margin-top: 10px;
                background: white;
                color: #667eea;
                border: none;
                padding: 5px 15px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
            ">关闭</button>
        `;
        
        document.body.appendChild(tip);
        
        // 10秒后自动隐藏
        setTimeout(() => {
            if (tip.parentElement) {
                tip.remove();
            }
        }, 10000);
    }
}

// 全局函数：打开启动管理器
function openLauncher() {
    window.open('启动管理器.html', '_blank');
}

// 全局函数：显示连接状态
async function checkConnection() {
    if (window.nuwa) {
        return await window.nuwa.checkConnectionStatus();
    }
    return false;
}

// 初始化应用
const nuwa = new NuwaFrontend();
window.nuwa = nuwa; // 暴露到全局，便于调试和调用