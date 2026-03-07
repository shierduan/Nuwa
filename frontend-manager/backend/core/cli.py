"""
CLI调试工具

功能：
- 查看和修改配置
- 监控实时变更
- 健康检查
- 历史记录查询
- 回滚操作
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich import print as rprint

from config import AsyncConfigManager
from core import setup_logger

console = Console()


class ConfigCLI:
    """配置管理CLI工具"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config_manager = AsyncConfigManager(config_path)
        self.logger = setup_logger("cli", "INFO")
    
    async def view(self, section: Optional[str] = None):
        """查看配置"""
        try:
            config = await self.config_manager.load()
            data = config.to_dict()
            
            if section:
                if section in data:
                    console.print(f"\n[bold cyan]配置 section: {section}[/]")
                    console.print_json(json.dumps({section: data[section]}, indent=2))
                else:
                    console.print(f"[red]❌ 配置项不存在: {section}[/]")
            else:
                console.print("\n[bold green]当前配置[/]")
                console.print_json(json.dumps(data, indent=2))
                
        except Exception as e:
            console.print(f"[red]❌ 错误: {e}[/]")
    
    async def set_config(self, key: str, value: str):
        """设置配置项"""
        try:
            # 解析值类型
            parsed_value = self._parse_value(value)
            
            # 加载当前配置
            config = await self.config_manager.load()
            old_value = getattr(config, key, None)
            
            if old_value is None:
                console.print(f"[yellow]⚠️  警告: 配置项 '{key}' 不存在，将创建新项[/]")
            
            # 执行更新
            await self.config_manager.update({key: parsed_value}, user="cli")
            
            console.print(f"[green]✅ 配置已更新[/]")
            console.print(f"   {key}: {old_value} → {parsed_value}")
            
        except ValueError as e:
            console.print(f"[red]❌ 验证错误: {e}[/]")
        except Exception as e:
            console.print(f"[red]❌ 错误: {e}[/]")
    
    async def history(self, limit: int = 20):
        """查看历史记录"""
        try:
            history = await self.config_manager.get_history(limit)
            
            if not history:
                console.print("[yellow]暂无历史记录[/]")
                return
            
            table = Table(title=f"配置变更历史 (最近 {len(history)} 条)")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("时间", style="magenta")
            table.add_column("用户", style="green")
            table.add_column("状态", style="yellow")
            table.add_column("变更内容", style="white")
            
            for record in reversed(history):  # 最新在前
                changes = ", ".join(record["updates"].keys())
                status_icon = "✅" if record["status"] == "committed" else "🔄"
                
                table.add_row(
                    record["id"][:8],
                    record["timestamp"][:19],
                    record["user"],
                    f"{status_icon} {record['status']}",
                    changes[:30]
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]❌ 错误: {e}[/]")
    
    async def rollback(self, history_id: str):
        """回滚到历史版本"""
        try:
            success = await self.config_manager.rollback_to_history(history_id)
            
            if success:
                console.print(f"[green]✅ 已回滚到 {history_id}[/]")
            else:
                console.print(f"[red]❌ 历史记录不存在: {history_id}[/]")
                
        except Exception as e:
            console.print(f"[red]❌ 回滚失败: {e}[/]")
    
    async def watch(self):
        """实时监控配置变更"""
        console.print("[yellow]🔄 正在监控配置变更... (Ctrl+C 退出)[/]")
        console.print(f"[dim]配置文件: {self.config_path}[/]\n")
        
        # 获取初始配置
        last_config = None
        try:
            config = await self.config_manager.load()
            last_config = config.to_dict()
        except:
            pass
        
        try:
            with Live(auto_refresh=False) as live:
                while True:
                    try:
                        # 检查文件修改时间
                        if Path(self.config_path).exists():
                            current_mtime = Path(self.config_path).stat().st_mtime
                            
                            # 重新加载配置
                            current_config = await self.config_manager.get_raw_config()
                            
                            # 检查是否有变化
                            if current_config != last_config and last_config is not None:
                                # 显示变更
                                changes = self._find_changes(last_config, current_config)
                                
                                if changes:
                                    timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
                                    
                                    panel = Panel(
                                        f"[bold green]检测到配置变更 ({timestamp})[/]\n\n"
                                        + "\n".join([f"  {k}: {v}" for k, v in changes.items()]),
                                        title="[bold cyan]配置更新[/]",
                                        border_style="green"
                                    )
                                    
                                    rprint(panel)
                            
                            last_config = current_config
                        
                        await asyncio.sleep(1)
                        
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        console.print(f"[red]监控错误: {e}[/]")
                        await asyncio.sleep(2)
                        
        except KeyboardInterrupt:
            console.print("\n[green]✅ 监控已停止[/]")
    
    async def health(self):
        """健康检查"""
        console.print("\n[bold cyan]🔍 系统健康检查[/]\n")
        
        checks = []
        
        # 1. 配置文件
        try:
            config = await self.config_manager.load()
            checks.append(("配置文件", "✅", "green", f"已加载 {len(config.to_dict())} 项"))
        except Exception as e:
            checks.append(("配置文件", "❌", "red", str(e)))
        
        # 2. 备份文件
        backup_path = Path(f"{self.config_path}.backup")
        if backup_path.exists():
            checks.append(("备份文件", "✅", "green", "存在"))
        else:
            checks.append(("备份文件", "⚠️", "yellow", "不存在"))
        
        # 3. 历史记录
        history_path = Path(f"{self.config_path}.history.json")
        if history_path.exists():
            try:
                history = await self.config_manager.get_history(1)
                checks.append(("历史记录", "✅", "green", f"{len(history)} 条记录"))
            except:
                checks.append(("历史记录", "⚠️", "yellow", "可读但异常"))
        else:
            checks.append(("历史记录", "⚠️", "yellow", "不存在"))
        
        # 4. 统计信息
        stats = self.config_manager.get_stats()
        checks.append(("运行时间", "✅", "green", f"{stats['uptime_seconds']:.1f} 秒"))
        checks.append(("事务数", "✅", "green", str(stats['transaction_count'])))
        
        # 显示结果
        table = Table(show_header=False, expand=True)
        table.add_column("检查项", style="bold")
        table.add_column("状态", justify="center")
        table.add_column("详情", style="dim")
        
        for name, status, color, detail in checks:
            table.add_row(name, f"[{color}]{status}[/]", detail)
        
        console.print(table)
        
        # 总体状态
        healthy = all(c[1] == "✅" for c in checks)
        if healthy:
            console.print("\n[bold green]🟢 系统状态: 健康[/]")
        else:
            console.print("\n[bold yellow]🟡 系统状态: 需要关注[/]")
    
    async def stats(self):
        """显示统计信息"""
        stats = self.config_manager.get_stats()
        
        panel = Panel(
            f"[bold cyan]📊 配置管理器统计[/]\n\n"
            f"[green]配置已加载:[/] {stats['config_loaded']}\n"
            f"[green]配置路径:[/] {stats['config_path']}\n"
            f"[green]备份存在:[/] {stats['backup_exists']}\n"
            f"[green]历史记录:[/] {stats['history_exists']}\n"
            f"[green]事务数量:[/] {stats['transaction_count']}\n"
            f"[green]回调数量:[/] {stats['callback_count']}\n"
            f"[green]运行时间:[/] {stats['uptime_seconds']:.1f} 秒\n"
            f"[green]启动时间:[/] {stats['start_time']}",
            title="统计信息",
            border_style="blue"
        )
        
        console.print(panel)
    
    def _parse_value(self, value: str):
        """智能解析值类型"""
        # 布尔值
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        
        # 数字
        if value.isdigit():
            return int(value)
        try:
            if value.replace('.', '').isdigit():
                return float(value)
        except:
            pass
        
        # JSON对象
        if value.startswith("{") and value.endswith("}"):
            try:
                return json.loads(value)
            except:
                pass
        
        # JSON数组
        if value.startswith("[") and value.endswith("]"):
            try:
                return json.loads(value)
            except:
                pass
        
        # 字符串
        return value
    
    def _find_changes(self, old: dict, new: dict, prefix: str = "") -> dict:
        """找出配置变更"""
        changes = {}
        
        for key, value in new.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if key not in old:
                changes[full_key] = f"(新增) {value}"
            elif old[key] != value:
                changes[full_key] = f"{old[key]} → {value}"
            elif isinstance(value, dict):
                sub_changes = self._find_changes(old[key], value, full_key)
                changes.update(sub_changes)
        
        return changes


# Click命令行接口
@click.group()
def cli():
    """女娲配置管理CLI工具"""
    pass


@cli.command()
@click.argument("section", required=False)
@click.option("--config", default="config/config.yaml", help="配置文件路径")
async def view(section, config):
    """查看配置"""
    cli_tool = ConfigCLI(config)
    await cli_tool.view(section)


@cli.command()
@click.argument("key")
@click.argument("value")
@click.option("--config", default="config/config.yaml", help="配置文件路径")
async def set(key, value, config):
    """设置配置项"""
    cli_tool = ConfigCLI(config)
    await cli_tool.set_config(key, value)


@cli.command()
@click.option("--limit", default=20, help="显示数量")
@click.option("--config", default="config/config.yaml", help="配置文件路径")
async def history(limit, config):
    """查看历史记录"""
    cli_tool = ConfigCLI(config)
    await cli_tool.history(limit)


@cli.command()
@click.argument("history_id")
@click.option("--config", default="config/config.yaml", help="配置文件路径")
async def rollback(history_id, config):
    """回滚到历史版本"""
    cli_tool = ConfigCLI(config)
    await cli_tool.rollback(history_id)


@cli.command()
@click.option("--config", default="config/config.yaml", help="配置文件路径")
async def watch(config):
    """实时监控配置变更"""
    cli_tool = ConfigCLI(config)
    await cli_tool.watch()


@cli.command()
@click.option("--config", default="config/config.yaml", help="配置文件路径")
async def health(config):
    """健康检查"""
    cli_tool = ConfigCLI(config)
    await cli_tool.health()


@cli.command()
@click.option("--config", default="config/config.yaml", help="配置文件路径")
async def stats(config):
    """显示统计信息"""
    cli_tool = ConfigCLI(config)
    await cli_tool.stats()


if __name__ == "__main__":
    # 支持异步命令
    import asyncio
    
    def async_cmd(coro):
        def wrapper(*args, **kwargs):
            return asyncio.run(coro(*args, **kwargs))
        return wrapper
    
    # 包装异步命令
    for cmd in [view, set, history, rollback, watch, health, stats]:
        cli.command()(async_cmd(cmd.__wrapped__))
    
    cli()