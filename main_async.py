#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
女娲控制台应用 - 统一异步版本

使用新的 NuwaKernelAsync，消除同步/异步混用问题。
"""

import asyncio
import sys
import os
import time
import logging
from typing import Optional, Dict
from datetime import datetime
from colorama import init, Fore, Style

# 配置 logging 模块
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)

# 导入新的统一异步内核
from nuwa_core.nuwa_kernel_async import NuwaKernelAsync
from nuwa_core.nuwa_state import NuwaState
from nuwa_core.config_manager import NuwaConfig
from nuwa_core.metrics_collector import init_metrics_collector, MetricsConfig

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config", "config.yaml")

# 初始化 colorama（Windows 需要）
init(autoreset=True)

# 颜色常量定义
COLOR_SYSTEM = Fore.GREEN  # 系统提示
COLOR_USER = Fore.CYAN     # 用户输入
COLOR_NUWA = Fore.WHITE    # 女娲回复
COLOR_MONITOR = Fore.MAGENTA  # 后台监控
COLOR_STATUS = Fore.YELLOW     # 状态显示
COLOR_ERROR = Fore.RED         # 错误信息
COLOR_CACHE = Fore.BLUE        # 缓存提示


class NuwaConsoleAsync:
    """女娲控制台应用（统一异步版本）"""
    
    def __init__(
        self, 
        log_thoughts: bool = True, 
        log_file: str = "nuwa.log", 
        data_dir: str = "data", 
        project_name: str = "nuwa",
        enable_cache: bool = True
    ):
        self.kernel: Optional[NuwaKernelAsync] = None
        self.running = False
        self.log_thoughts = log_thoughts
        self.log_file = log_file
        self.data_dir = data_dir
        self.project_name = project_name
        self.enable_cache = enable_cache
        self.feishu_channel = None  # 飞书渠道实例
        
        self.state_file_path = os.path.join(data_dir, project_name, "state.json")
        self._prev_monitor_snapshot: Optional[Dict[str, float]] = None
        self.show_thought_in_console: bool = True
    
    def handle_active_message(self, text: str):
        """处理主动消息回调"""
        print(f"{COLOR_NUWA}\n女娲 (主动) > {text}{Style.RESET_ALL}\n")
        
        # 同步发送到飞书（如果已配置）
        if self.feishu_channel:
            try:
                # 从配置中获取飞书主动消息发送目标
                import yaml
                config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
                with open(config_path, 'r', encoding='utf-8') as f:
                    raw_config = yaml.safe_load(f)
                
                feishu_config = raw_config.get('channels', {}).get('feishu', {})
                active_target = feishu_config.get('active_message_target', '')
                
                if active_target:
                    print(f"{COLOR_SYSTEM}📱 发送主动消息到飞书：{active_target}{Style.RESET_ALL}")
                    success = self.feishu_channel.send_message(text, active_target)
                    if success:
                        print(f"{COLOR_SYSTEM}📱 主动消息已发送到飞书{Style.RESET_ALL}")
                    else:
                        print(f"{COLOR_ERROR}📱 发送主动消息到飞书失败{Style.RESET_ALL}")
                # 未配置时不显示警告，静默处理
            except Exception as e:
                print(f"{COLOR_ERROR}📱 发送主动消息到飞书失败：{e}{Style.RESET_ALL}")
    
    async def initialize(self):
        """初始化内核"""
        print(f"{COLOR_SYSTEM}正在初始化女娲内核（统一异步架构）...")
        
        try:
            # 检查状态文件
            if os.path.exists(self.state_file_path):
                print(f"{COLOR_SYSTEM}📂 发现状态文件：{self.state_file_path}")
            
            # 加载配置文件
            config = NuwaConfig.from_file(CONFIG_FILE)
            print(f"{COLOR_SYSTEM}📝 加载配置文件：{CONFIG_FILE}")
            
            # 初始化监控服务
            metrics_config = MetricsConfig(http_port=config.metrics_port)
            init_metrics_collector(metrics_config)
            print(f"{COLOR_SYSTEM}📊 监控服务已启动，端口：{config.metrics_port}")
            
            # 使用新的统一异步内核
            self.kernel = NuwaKernelAsync(
                project_name=self.project_name,
                data_dir=self.data_dir,
                base_url=config.llm_base_url,
                api_key=config.llm_api_key,
                model_name=config.llm_model_name,
                on_message_callback=self.handle_active_message,
                enable_cache=self.enable_cache,
                cache_ttl=300,
                enable_tts=False,  # 默认禁用 TTS
                enable_live2d=False,  # 默认禁用 Live2D
                max_tokens=config.llm_max_tokens,
            )
            
            # 初始化飞书渠道
            try:
                print(f"{COLOR_SYSTEM}📱 开始初始化飞书渠道...")
                from nuwa_core.chat_channels.feishu_channel import FeishuChannel
                
                # 直接从配置文件读取，不依赖 NuwaConfig
                import yaml
                config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
                with open(config_path, 'r', encoding='utf-8') as f:
                    raw_config = yaml.safe_load(f)
                
                channels_config = raw_config.get('channels', {})
                feishu_config = channels_config.get('feishu', {})
                
                print(f"{COLOR_SYSTEM}📱 飞书配置：{feishu_config}")
                
                if feishu_config.get('enabled', False):
                    print(f"{COLOR_SYSTEM}📱 飞书渠道已启用，正在启动...")
                    self.feishu_channel = FeishuChannel(feishu_config, self.kernel)
                    # 先设置主事件循环引用，确保子线程中可以安全地执行异步任务
                    try:
                        main_loop = asyncio.get_running_loop()
                        self.feishu_channel.set_event_loop(main_loop)
                        print(f"{COLOR_SYSTEM}📱 已设置飞书渠道的事件循环引用")
                    except RuntimeError:
                        print(f"{COLOR_ERROR}⚠️ 无法获取运行中的事件循环，飞书消息处理可能受限")
                    
                    if self.feishu_channel.start_ws_client():
                        print(f"{COLOR_SYSTEM}📱 飞书渠道已启动")
                        # 测试连接
                        probe_result = self.feishu_channel.probe()
                        if probe_result.get('status') == 'ok':
                            print(f"{COLOR_SYSTEM}✅ 飞书连接测试成功")
                        else:
                            print(f"{COLOR_ERROR}❌ 飞书连接测试失败：{probe_result.get('message', 'Unknown error')}")
                    else:
                        print(f"{COLOR_ERROR}❌ 飞书渠道启动失败")
                else:
                    print(f"{COLOR_SYSTEM}📱 飞书渠道未启用")
            except Exception as e:
                print(f"{COLOR_ERROR}❌ 初始化飞书渠道失败：{e}")
                import traceback
                traceback.print_exc()
            
            # 启动心跳循环
            self.kernel.start_heartbeat()
            
            self.running = True
            
            print(f"{COLOR_SYSTEM}[OK] Nuwa Kernel started (Unified Async Architecture){Style.RESET_ALL}")
            print(f"{COLOR_SYSTEM}💓 心跳循环已启动")
            if self.enable_cache:
                print(f"{COLOR_SYSTEM}💾 缓存系统已启用")
            print(f"{COLOR_SYSTEM}📊 监控服务已启动，端口：{config.metrics_port}")
            print(f"{COLOR_SYSTEM}📝 输入 'exit' 或 'quit' 退出，输入 '/status' 查看状态")
            print(f"{COLOR_SYSTEM}📝 输入 '/cache' 查看缓存统计，输入 '/clear' 清空缓存")
            print()
            
        except Exception as e:
            print(f"{COLOR_ERROR}[ERROR] Initialization failed: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def _handle_debug_set(self, command: str):
        """处理 /set 指令"""
        if not self.kernel or not self.kernel.state:
            print(f"{COLOR_ERROR}内核未初始化")
            return

        parts = command.split()
        if len(parts) != 3:
            print(f"{COLOR_ERROR}格式错误。用法：/set [key] [value]")
            return

        key, val_str = parts[1], parts[2]
        try:
            value = float(val_str)
        except ValueError:
            print(f"{COLOR_ERROR}数值格式错误：{val_str}")
            return

        state = self.kernel.state
        found = False

        if hasattr(state, key):
            setattr(state, key, value)
            found = True
        elif key == "entropy":
            state.system_entropy = value
            found = True
        elif key in state.emotional_spectrum:
            state.emotional_spectrum[key] = value
            found = True
        elif key in state.drives:
            state.drives[key] = value
            found = True
        elif key == "hunger":
            state.drives["social_hunger"] = value
            found = True

        if found:
            state.clamp_values()
            print(f"{COLOR_SYSTEM}[DEBUG] {key} set to {value}{Style.RESET_ALL}")
            self._print_monitor_snapshot(self._capture_state_snapshot(state))
        else:
            print(f"{COLOR_ERROR}[ERROR] Property not found: {key}{Style.RESET_ALL}")
    
    async def console_loop(self):
        """交互循环"""
        while self.running:
            try:
                user_input = await asyncio.to_thread(
                    input, f"{COLOR_USER}你：{Style.RESET_ALL}"
                )
                
                if not user_input.strip():
                    continue
                
                user_input = user_input.strip()
                
                # 退出指令
                if user_input.lower() in ['exit', 'quit']:
                    print(f"{COLOR_SYSTEM}正在退出...")
                    if self.kernel and self.kernel.state:
                        if self.kernel.state.save(self.state_file_path):
                            print(f"{COLOR_SYSTEM}💾 状态已保存")
                    self.running = False
                    break
                
                # 状态查看
                if user_input == '/status':
                    await self._show_status()
                    continue
                
                # 缓存统计
                if user_input == '/cache':
                    await self._show_cache_stats()
                    continue
                
                # 清空缓存
                if user_input == '/clear':
                    if self.kernel:
                        self.kernel.clear_cache()
                        print(f"{COLOR_SYSTEM}[OK] Cache cleared{Style.RESET_ALL}")
                    continue
                
                # 触发做梦
                if user_input == '/dream':
                    await self._run_memory_dream()
                    continue
                
                # 调试设置
                if user_input.startswith('/set '):
                    self._handle_debug_set(user_input)
                    continue
                
                # 技能管理命令
                if user_input.startswith('/skills '):
                    skill_command = user_input[7:].strip()
                    if not skill_command:
                        continue
                    
                    # 解析技能命令
                    parts = skill_command.split()
                    if not parts:
                        continue
                    
                    cmd = parts[0].lower()
                    args = parts[1:]
                    
                    if cmd == 'search' and args:
                        # 搜索技能
                        query = ' '.join(args)
                        print(f"{COLOR_SYSTEM}搜索技能：{query}{Style.RESET_ALL}")
                        results = await self.kernel.search_skills(query)
                        if results:
                            print(f"{COLOR_SYSTEM}搜索结果 ({len(results)} 个):{Style.RESET_ALL}")
                            for i, skill in enumerate(results):
                                print(f"{COLOR_SYSTEM}  {i+1}. {skill.get('name')} ({skill.get('slug')}) - 分数：{skill.get('score')}{Style.RESET_ALL}")
                        else:
                            print(f"{COLOR_SYSTEM}未找到相关技能{Style.RESET_ALL}")
                    elif cmd == 'install' and args:
                        # 安装技能
                        skill_slug = args[0]
                        version = args[1] if len(args) > 1 else None
                        print(f"{COLOR_SYSTEM}安装技能：{skill_slug}{Style.RESET_ALL}")
                        success = await self.kernel.install_skill(skill_slug, version)
                        if success:
                            print(f"{COLOR_SYSTEM}技能安装成功{Style.RESET_ALL}")
                        else:
                            print(f"{COLOR_SYSTEM}技能安装失败{Style.RESET_ALL}")
                    elif cmd == 'uninstall' and args:
                        # 卸载技能
                        skill_slug = args[0]
                        print(f"{COLOR_SYSTEM}卸载技能：{skill_slug}{Style.RESET_ALL}")
                        success = await self.kernel.uninstall_skill(skill_slug)
                        if success:
                            print(f"{COLOR_SYSTEM}技能卸载成功{Style.RESET_ALL}")
                        else:
                            print(f"{COLOR_SYSTEM}技能卸载失败{Style.RESET_ALL}")
                    elif cmd == 'list':
                        # 列出技能
                        print(f"{COLOR_SYSTEM}列出已安装的技能:{Style.RESET_ALL}")
                        skills = await self.kernel.list_skills()
                        if skills:
                            for i, skill in enumerate(skills):
                                print(f"{COLOR_SYSTEM}  {i+1}. {skill.get('name')} ({skill.get('slug')}){Style.RESET_ALL}")
                        else:
                            print(f"{COLOR_SYSTEM}没有已安装的技能{Style.RESET_ALL}")
                    else:
                        print(f"{COLOR_SYSTEM}技能命令格式错误，使用：/skills [search|install|uninstall|list] [参数]{Style.RESET_ALL}")
                    continue
                
                # 系统指令
                if user_input.startswith('/sys '):
                    sys_instruction = user_input[5:].strip()
                    if not sys_instruction:
                        continue
                    print(f"{COLOR_MONITOR}[*] Sending system instruction: {sys_instruction}{Style.RESET_ALL}")
                    result = await self.kernel.process_input(
                        user_input="",
                        system_instruction=sys_instruction,
                    )
                    user_input = "[SYS]" + sys_instruction
                else:
                    result = None
                
                # 正常对话
                if not self.kernel:
                    print(f"{COLOR_ERROR}内核未初始化")
                    continue
                
                if result is None:
                    print(f"{COLOR_NUWA}女娲思考中...{Style.RESET_ALL}")
                    result = await self.kernel.process_input(user_input)
                
                # 处理思维
                thought = result.get("thought", "")
                if thought:
                    if self.log_thoughts:
                        self._log_thought(user_input, thought)
                    
                    if self.show_thought_in_console:
                        print(f"{COLOR_MONITOR}[思维] {thought}{Style.RESET_ALL}")
                
                # 显示回复
                if result.get("reply"):
                    print(f"{COLOR_NUWA}[回复] 女娲：{result['reply']}{Style.RESET_ALL}\n")
                elif result.get("error"):
                    print(f"{COLOR_ERROR}错误：{result['error']}{Style.RESET_ALL}\n")
                
                # 输出状态快照
                if self.kernel and self.kernel.state:
                    snapshot = self._capture_state_snapshot(self.kernel.state)
                    self._print_monitor_snapshot(snapshot)
                    self._prev_monitor_snapshot = snapshot
                    
                    # 自动保存
                    if self.kernel.state.save(self.state_file_path):
                        pass  # 静默保存
                
            except EOFError:
                print(f"\n{COLOR_SYSTEM}检测到 EOF，正在退出...")
                self.running = False
                break
            except KeyboardInterrupt:
                print(f"\n{COLOR_SYSTEM}检测到中断信号，正在退出...")
                self.running = False
                break
            except Exception as e:
                print(f"{COLOR_ERROR}处理输入时出错：{e}{Style.RESET_ALL}\n")
                import traceback
                traceback.print_exc()
    
    async def _show_status(self):
        """显示当前状态"""
        if not self.kernel:
            print(f"{COLOR_ERROR}内核未初始化")
            return
        
        state = self.kernel.state
        
        print(f"\n{COLOR_STATUS}{'='*50}")
        print(f"{COLOR_STATUS}【女娲状态 - 上帝视角】")
        print(f"{COLOR_STATUS}{'='*50}")
        print(f"{COLOR_STATUS}精力 (Energy): {state.energy:.3f}")
        print(f"{COLOR_STATUS}熵值 (System Entropy): {state.system_entropy:.3f}")
        print(f"{COLOR_STATUS}")
        print(f"{COLOR_STATUS}【情绪谱 (Emotional Spectrum)】")
        for emotion, value in state.emotional_spectrum.items():
            print(f"{COLOR_STATUS}  - {emotion:15s}: {value:.3f}")
        print(f"{COLOR_STATUS}")
        print(f"{COLOR_STATUS}【驱动力 (Drives)】")
        for drive, value in state.drives.items():
            print(f"{COLOR_STATUS}  - {drive:15s}: {value:.3f}")
        print(f"{COLOR_STATUS}")
        print(f"{COLOR_STATUS}亲密度 (Rapport): {state.rapport:.3f}")
        print(f"{COLOR_STATUS}运行时间 (Uptime): {state.uptime:.1f} 秒")
        print(f"{COLOR_STATUS}{'='*50}\n{Style.RESET_ALL}")
    
    async def _show_cache_stats(self):
        """显示缓存统计"""
        if not self.kernel:
            print(f"{COLOR_ERROR}内核未初始化")
            return
        
        stats = self.kernel.get_cache_stats()
        
        print(f"\n{COLOR_CACHE}{'='*40}")
        print(f"{COLOR_CACHE}【缓存统计】")
        print(f"{COLOR_CACHE}{'='*40}")
        
        if "error" in stats:
            print(f"{COLOR_CACHE}[WARN] {stats['error']}{Style.RESET_ALL}")
        else:
            for key, value in stats.items():
                print(f"{COLOR_CACHE}{key}: {value}")
        
        print(f"{COLOR_CACHE}{'='*40}\n{Style.RESET_ALL}")
    
    async def _run_memory_dream(self):
        """手动触发做梦系统"""
        if not self.kernel:
            print(f"{COLOR_ERROR}内核未初始化")
            return
        
        print(f"{COLOR_SYSTEM}🌙 正在触发 Memory Dreamer...")
        success = await self.kernel.run_memory_dream()
        if success:
            print(f"{COLOR_SYSTEM}🌙 Memory Dreamer 完成。")
        else:
            print(f"{COLOR_ERROR}[WARN] Memory Dreamer failed to run.{Style.RESET_ALL}")
    
    def _log_thought(self, user_input: str, thought: str):
        """将思维记录到日志文件"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] 用户：{user_input}\n思维：{thought}\n{'='*60}\n"
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            pass
    
    def _capture_state_snapshot(self, state) -> Dict[str, float]:
        """捕获当前状态快照"""
        return {
            "energy": state.energy,
            "system_entropy": state.system_entropy,
            "rapport": state.rapport,
            "drives": state.drives.copy(),
            "emotions": state.emotional_spectrum.copy(),
        }
    
    def _print_monitor_snapshot(self, snapshot: Dict[str, float]):
        """打印详细的状态监控信息"""
        drives = snapshot["drives"]
        emotions = snapshot["emotions"]

        # 情绪中文映射
        emotion_name_map = {
            "joy": "快乐",
            "anger": "愤怒",
            "sadness": "悲伤",
            "fear": "恐惧",
            "trust": "信任",
            "anticipation": "期待",
        }
        emotion_line = " | ".join(
            [f"{emotion_name_map.get(k, k)}:{v:.3f}" for k, v in emotions.items()]
        )

        print(
            f"{COLOR_MONITOR}[生理监控] 精力：{snapshot['energy']:.4f} | 混乱度：{snapshot['system_entropy']:.4f} | 亲密度：{snapshot['rapport']:.4f}{Style.RESET_ALL}"
        )
        print(
            f"{COLOR_MONITOR}              驱动力 -> 社交饥渴：{drives.get('social_hunger', 0.0):.4f} | 好奇心：{drives.get('curiosity', 0.0):.4f}{Style.RESET_ALL}"
        )
        print(f"{COLOR_MONITOR}              情绪谱 -> {emotion_line}{Style.RESET_ALL}")
    
    async def monitor_loop(self):
        """后台监控循环"""
        while not self.kernel or not self.running:
            await asyncio.sleep(0.1)
        
        last_forced_output = time.time()
        force_output_interval = 60.0
        
        while self.running:
            try:
                await asyncio.sleep(10.0)
                
                if not self.kernel or not self.running:
                    break
                
                state = self.kernel.state
                snapshot = self._capture_state_snapshot(state)
                
                current_time = time.time()
                should_force_output = (current_time - last_forced_output) >= force_output_interval
                
                if self._prev_monitor_snapshot is None or self._has_significant_change(self._prev_monitor_snapshot, snapshot) or should_force_output:
                    self._print_monitor_snapshot(snapshot)
                    self._prev_monitor_snapshot = snapshot
                    if should_force_output:
                        last_forced_output = current_time
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                pass
    
    def _has_significant_change(self, previous: Dict[str, float], current: Dict[str, float], threshold: float = 0.005) -> bool:
        """判断状态是否发生显著变化"""
        if abs(previous["energy"] - current["energy"]) > threshold:
            return True
        if abs(previous["system_entropy"] - current["system_entropy"]) > threshold:
            return True
        if abs(previous["rapport"] - current["rapport"]) > threshold:
            return True
        
        for drive, value in current["drives"].items():
            if abs(previous["drives"].get(drive, 0.0) - value) > threshold:
                return True
        
        for emotion, value in current["emotions"].items():
            if abs(previous["emotions"].get(emotion, 0.0) - value) > threshold * 1.5:
                return True
        
        return False
    
    async def cleanup(self):
        """清理资源"""
        if self.kernel:
            # 再次保存状态
            if self.kernel.state:
                if self.kernel.state.save(self.state_file_path):
                    print(f"{COLOR_SYSTEM}💾 状态已保存")
            
            self.kernel.stop_heartbeat()
            print(f"{COLOR_SYSTEM}[OK] Heartbeat loop stopped{Style.RESET_ALL}")
        
        print(f"{COLOR_SYSTEM}👋 再见！")


async def main():
    """主程序入口"""
    console = NuwaConsoleAsync(enable_cache=True)
    
    try:
        # 初始化
        await console.initialize()
        
        # 同时运行交互循环和监控循环
        await asyncio.gather(
            console.console_loop(),
            console.monitor_loop(),
            return_exceptions=True,
        )
    
    except KeyboardInterrupt:
        print(f"\n{COLOR_SYSTEM}检测到中断信号，正在退出...")
    except Exception as e:
        print(f"{COLOR_ERROR}程序异常：{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        await console.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{COLOR_SYSTEM}程序已退出")
    except Exception as e:
        print(f"{COLOR_ERROR}启动失败：{e}")
        sys.exit(1)