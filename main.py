"""
女娲 (Nuwa) - MVP 启动脚本

异步控制台应用程序，提供交互式对话界面和后台监控。
"""

import asyncio
import sys
import os
import time
from typing import Optional, Dict
from datetime import datetime
from colorama import init, Fore, Style

from nuwa_core.nuwa_kernel import NuwaKernel
from nuwa_core.nuwa_state import NuwaState

# 初始化 colorama（Windows 需要）
init(autoreset=True)

# 颜色常量定义
COLOR_SYSTEM = Fore.GREEN  # 系统提示
COLOR_USER = Fore.CYAN  # 用户输入
COLOR_NUWA = Fore.WHITE  # 女娲回复
COLOR_MONITOR = Fore.MAGENTA  # 后台监控（暗色）
COLOR_STATUS = Fore.YELLOW  # 状态显示
COLOR_ERROR = Fore.RED  # 错误信息


class NuwaConsole:
    """女娲控制台应用"""
    
    def __init__(self, log_thoughts: bool = True, log_file: str = "nuwa.log", data_dir: str = "data", project_name: str = "nuwa"):
        """
        初始化控制台应用
        
        Args:
            log_thoughts: 是否将思维记录到日志文件（默认 True）
            log_file: 日志文件路径（默认 "nuwa.log"）
            data_dir: 数据目录（默认 "data"）
            project_name: 项目名称（默认 "nuwa"）
        """
        self.kernel: Optional[NuwaKernel] = None
        self.running = False
        self.log_thoughts = log_thoughts
        self.log_file = log_file
        self.data_dir = data_dir
        self.project_name = project_name
        # 状态文件路径
        self.state_file_path = os.path.join(data_dir, project_name, "state.json")
        self._prev_monitor_snapshot: Optional[Dict[str, float]] = None
        # 是否在终端显示思维内容（与实际对话区分开来）
        self.show_thought_in_console: bool = True
    
    def handle_active_message(self, text: str):
        """
        处理主动消息的回调函数
        
        Args:
            text: 主动生成的对话文本
        """
        print(f"{Fore.WHITE}\n女娲 (主动) > {text}{Style.RESET_ALL}\n")
    
    async def initialize(self):
        """初始化内核"""
        print(f"{COLOR_SYSTEM}正在初始化女娲内核...")
        
        try:
            # 检查并加载状态（如果存在）
            # 注意：NuwaKernel 内部也会加载状态，这里是为了确保状态文件存在时能被加载
            # 实际上 Kernel 会在初始化时自动加载，所以这里主要是显示状态
            if os.path.exists(self.state_file_path):
                print(f"{COLOR_SYSTEM}📂 发现状态文件: {self.state_file_path}")
            
            self.kernel = NuwaKernel(
                project_name=self.project_name,
                data_dir=self.data_dir,
                base_url="http://127.0.0.1:1234/v1",
                api_key="lm-studio",
                model_name="local-model",
                on_message_callback=self.handle_active_message,
            )
            
            # 启动心跳循环
            self.kernel.start_heartbeat()
            
            # 设置运行标志
            self.running = True
            
            print(f"{COLOR_SYSTEM}✅ 女娲内核已启动")
            print(f"{COLOR_SYSTEM}💓 心跳循环已启动")
            print(f"{COLOR_SYSTEM}📝 输入 'exit' 或 'quit' 退出，输入 '/status' 查看状态\n")
            
        except Exception as e:
            print(f"{COLOR_ERROR}❌ 初始化失败: {e}")
            sys.exit(1)
    
    def _handle_debug_set(self, command: str):
        """
        处理 /set 指令，允许动态修改状态.
        用法: /set energy 1.0 或 /set joy 0.8 或 /set hunger 0.5
        """
        if not self.kernel or not self.kernel.state:
            print(f"{COLOR_ERROR}内核未初始化")
            return

        parts = command.split()
        if len(parts) != 3:
            print(f"{COLOR_ERROR}格式错误。用法: /set [key] [value]")
            return

        key, val_str = parts[1], parts[2]
        try:
            value = float(val_str)
        except ValueError:
            print(f"{COLOR_ERROR}数值格式错误: {val_str}")
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
            print(f"{COLOR_SYSTEM}🔧 [Debug] {key} 已设置为 {value}")
            self._print_monitor_snapshot(self._capture_state_snapshot(state))
        else:
            print(f"{COLOR_ERROR}❌ 未找到属性: {key}")

    async def console_loop(self):
        """交互循环：监听用户输入并处理"""
        while self.running:
            try:
                # 使用 asyncio.to_thread 避免阻塞
                user_input = await asyncio.to_thread(
                    input, f"{COLOR_USER}你: {Style.RESET_ALL}"
                )
                
                if not user_input.strip():
                    continue
                
                user_input = user_input.strip()
                
                # 处理退出指令
                if user_input.lower() in ['exit', 'quit']:
                    print(f"{COLOR_SYSTEM}正在退出...")
                    # 退出前强制保存状态
                    if self.kernel and self.kernel.state:
                        if self.kernel.state.save(self.state_file_path):
                            print(f"{COLOR_SYSTEM}💾 状态已保存")
                    self.running = False
                    break
                
                # 处理状态查看指令
                if user_input == '/status':
                    await self._show_status()
                    continue
                
                # 触发做梦指令
                if user_input == '/dream':
                    await self._run_memory_dream()
                    continue

                if user_input.startswith('/set '):
                    self._handle_debug_set(user_input)
                    continue

                if user_input.startswith('/sys '):
                    sys_instruction = user_input[5:].strip()
                    if not sys_instruction:
                        continue
                    print(f"{COLOR_MONITOR}⚡ 发送系统指令: {sys_instruction}{Style.RESET_ALL}")
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
                
                # 调用内核处理输入
                if result is None:
                    print(f"{COLOR_NUWA}女娲思考中...{Style.RESET_ALL}")
                    result = await self.kernel.process_input(user_input)
                
                # 处理思维（不暴露给用户）
                thought = result.get("thought", "")
                if thought:
                    # 记录到日志文件
                    if self.log_thoughts:
                        self._log_thought(user_input, thought)
                    
                    # 可选：在控制台中以暗色显示模型思维，便于与实际对话区分
                    if self.show_thought_in_console:
                        print(f"{COLOR_MONITOR}[思维] {thought}{Style.RESET_ALL}")
                
                # 显示回复（用户可见，客户端只需解析这一行）
                if result.get("reply"):
                    # 使用清晰前缀，避免与其他日志中出现的"女娲:"混淆
                    print(f"{COLOR_NUWA}[回复] 女娲: {result['reply']}{Style.RESET_ALL}\n")
                elif result.get("error"):
                    print(f"{COLOR_ERROR}错误: {result['error']}{Style.RESET_ALL}\n")
                
                # 每次交互后输出状态快照（便于调试）
                if self.kernel and self.kernel.state:
                    # 输出生理监控信息
                    snapshot = self._capture_state_snapshot(self.kernel.state)
                    self._print_monitor_snapshot(snapshot)
                    # 更新监控快照（避免监控循环重复输出）
                    self._prev_monitor_snapshot = snapshot
                    
                    # 自动保存状态
                    if self.kernel.state.save(self.state_file_path):
                        # 静默保存，不打印消息（避免刷屏）
                        pass
                
            except EOFError:
                # Ctrl+D 退出
                print(f"\n{COLOR_SYSTEM}检测到 EOF，正在退出...")
                self.running = False
                break
            except KeyboardInterrupt:
                # Ctrl+C 退出
                print(f"\n{COLOR_SYSTEM}检测到中断信号，正在退出...")
                self.running = False
                break
            except Exception as e:
                print(f"{COLOR_ERROR}处理输入时出错: {e}{Style.RESET_ALL}\n")
    
    async def _show_status(self):
        """显示当前状态（上帝视角）"""
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
    
    async def monitor_loop(self):
        """后台监控循环：实时显示关键状态变化"""
        # 等待内核初始化完成
        while not self.kernel or not self.running:
            await asyncio.sleep(0.1)
        
        last_forced_output = time.time()
        force_output_interval = 60.0  # 每60秒强制输出一次（降低频率，因为交互时已输出）
        
        while self.running:
            try:
                await asyncio.sleep(10.0)  # 每 10 秒检查一次
                
                if not self.kernel or not self.running:
                    break
                
                state = self.kernel.state
                snapshot = self._capture_state_snapshot(state)
                
                current_time = time.time()
                should_force_output = (current_time - last_forced_output) >= force_output_interval
                
                # 如果有显著变化，或者到了强制输出时间，则输出
                # 注意：交互时已经输出，这里主要用于监控后台状态变化
                if self._prev_monitor_snapshot is None or self._has_significant_change(self._prev_monitor_snapshot, snapshot) or should_force_output:
                    self._print_monitor_snapshot(snapshot)
                    self._prev_monitor_snapshot = snapshot
                    if should_force_output:
                        last_forced_output = current_time
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # 监控循环出错不应该影响主程序
                pass
    
    def _log_thought(self, user_input: str, thought: str):
        """
        将思维记录到日志文件
        
        Args:
            user_input: 用户输入
            thought: 思维内容
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] 用户: {user_input}\n思维: {thought}\n{'='*60}\n"
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            # 日志写入失败不应该影响主程序
            pass
    
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
            print(f"{COLOR_ERROR}⚠️ Memory Dreamer 未能运行。")

    def _capture_state_snapshot(self, state) -> Dict[str, float]:
        """捕获当前状态快照，便于监控比较"""
        return {
            "energy": state.energy,
            "system_entropy": state.system_entropy,
            "rapport": state.rapport,
            "drives": state.drives.copy(),
            "emotions": state.emotional_spectrum.copy(),
        }

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

    def _print_monitor_snapshot(self, snapshot: Dict[str, float]):
        """打印详细的状态监控信息"""
        drives = snapshot["drives"]
        emotions = snapshot["emotions"]

        # 情绪中文映射，仅用于展示，内部字段仍保持英文键名
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

        # 终端显示使用中文标签，但内部字段名保持英文，避免兼容性问题
        print(
            f"{COLOR_MONITOR}[生理监控] 精力: {snapshot['energy']:.4f} | 混乱度: {snapshot['system_entropy']:.4f} | 亲密度: {snapshot['rapport']:.4f}{Style.RESET_ALL}"
        )
        print(
            f"{COLOR_MONITOR}              驱动力 -> 社交饥渴: {drives.get('social_hunger', 0.0):.4f} | 好奇心: {drives.get('curiosity', 0.0):.4f}{Style.RESET_ALL}"
        )
        print(f"{COLOR_MONITOR}              情绪谱 -> {emotion_line}{Style.RESET_ALL}")

    async def cleanup(self):
        """清理资源"""
        if self.kernel:
            # 停止心跳前再次保存状态（双重保险）
            if self.kernel.state:
                if self.kernel.state.save(self.state_file_path):
                    print(f"{COLOR_SYSTEM}💾 状态已保存")
            
            self.kernel.stop_heartbeat()
            print(f"{COLOR_SYSTEM}✅ 已停止心跳循环")
        print(f"{COLOR_SYSTEM}👋 再见！")


async def main():
    """主程序入口"""
    console = NuwaConsole()
    
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
        print(f"{COLOR_ERROR}程序异常: {e}")
    finally:
        # 清理资源
        await console.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{COLOR_SYSTEM}程序已退出")
    except Exception as e:
        print(f"{COLOR_ERROR}启动失败: {e}")
        sys.exit(1)

