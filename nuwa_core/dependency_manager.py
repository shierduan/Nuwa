"""
增强的依赖管理器 (Enhanced Dependency Manager)

特性:
- 自动检测和修复缺失的依赖
- 支持优雅降级（可选依赖缺失时不崩溃）
- 跨平台兼容（Windows/Linux/macOS）
- 智能镜像源切换
- 详细的安装指南和错误提示
"""

import sys
import subprocess
import os
from typing import Dict, List, Optional, Tuple


# ============================================================================
# 安全打印函数（避免 emoji 编码问题）
# ============================================================================

EMOJI_MAP = {
    '[OK]': '[OK]',
    '[ERROR]': '[ERROR]',
    '[WARN] ': '[WARN] ',
    '🔴': '[CRITICAL]',
    '🟡': '[WARNING]',
    '📦': '[PKG]',
    '🔧': '[FIX]',
    '📉': '[DEGRADED]',
    '❗': '[IMPORTANT]',
    'ℹ️ ': '[INFO] ',
    '📖': '[GUIDE]',
    '💡': '[TIP]',
}

def safe_print(msg: str) -> None:
    """安全打印，处理编码问题"""
    try:
        # 尝试直接打印
        print(msg)
    except UnicodeEncodeError:
        # 替换 emoji 为 ASCII
        for emoji, replacement in EMOJI_MAP.items():
            msg = msg.replace(emoji, replacement)
        # 替换其他可能的 emoji
        msg = msg.replace('•', '-')
        msg = msg.replace('\u2705', '[OK]')  # [OK]
        msg = msg.replace('\u274c', '[ERROR]')  # [ERROR]
        print(msg)


class DependencyManager:
    """增强的依赖管理器，具备自修复能力"""
    
    # 关键依赖（系统运行必需）
    CRITICAL_DEPS = {
        'pyyaml': {'import_name': 'yaml', 'package': 'pyyaml>=6.0'},
        'psutil': {'import_name': 'psutil', 'package': 'psutil>=5.9.0'},
    }
    
    # 可选依赖（用于高级功能，缺失时优雅降级）
    OPTIONAL_DEPS = {
        'pyarrow': {
            'import_name': 'pyarrow', 
            'package': 'pyarrow>=12.0.0',
            'feature': '向量数据库支持',
            'critical_for': ['memory_cortex'],
            'graceful_degradation': '记忆存储功能将不可用'
        },
        'lancedb': {
            'import_name': 'lancedb', 
            'package': 'lancedb>=0.5.0',
            'feature': '记忆存储功能',
            'critical_for': ['memory_cortex'],
            'graceful_degradation': '使用简单的内存存储替代'
        },
        'sentence_transformers': {
            'import_name': 'sentence_transformers',
            'package': 'sentence-transformers>=2.2.0',
            'feature': '语义嵌入功能',
            'critical_for': ['memory_cortex'],
            'graceful_degradation': '使用简单的文本匹配替代语义检索'
        },
        'numpy': {
            'import_name': 'numpy', 
            'package': 'numpy>=1.24.0',
            'feature': '科学计算支持',
            'critical_for': [],
            'graceful_degradation': '数值计算性能下降'
        },
        'torch': {
            'import_name': 'torch', 
            'package': 'torch>=2.0.0',
            'feature': '深度学习框架',
            'critical_for': [],
            'graceful_degradation': 'AI 推理功能受限'
        },
        'fastapi': {
            'import_name': 'fastapi', 
            'package': 'fastapi>=0.95.0',
            'feature': 'Web API 服务',
            'critical_for': ['web_server'],
            'graceful_degradation': 'Web API 不可用，仅支持命令行'
        },
        'uvicorn': {
            'import_name': 'uvicorn', 
            'package': 'uvicorn[standard]>=0.21.0',
            'feature': 'ASGI 服务器',
            'critical_for': ['web_server'],
            'graceful_degradation': 'WebSocket 服务不可用'
        },
    }
    
    # 国内镜像源（用于加速安装）
    MIRRORS = [
        ('清华大学', 'https://pypi.tuna.tsinghua.edu.cn/simple'),
        ('阿里云', 'https://mirrors.aliyun.com/pypi/simple/'),
        ('豆瓣', 'https://pypi.douban.com/simple/'),
        ('中科大', 'https://pypi.mirrors.ustc.edu.cn/simple/'),
    ]
    
    def __init__(self):
        self.installed: Dict[str, bool] = {}
        self.missing: List[str] = []
        self.failed_imports: List[Dict] = []
        self.degraded_features: List[str] = []
        self.install_attempts: Dict[str, int] = {}
        
    def check_all(self, include_optional: bool = True) -> bool:
        """检查所有依赖"""
        all_deps = {**self.CRITICAL_DEPS}
        if include_optional:
            all_deps.update(self.OPTIONAL_DEPS)
        
        for pkg_name, info in all_deps.items():
            try:
                __import__(info['import_name'])
                self.installed[pkg_name] = True
            except ImportError as e:
                self.installed[pkg_name] = False
                self.missing.append(pkg_name)
                self.failed_imports.append({
                    'package': pkg_name,
                    'import_name': info['import_name'],
                    'error': str(e),
                    'is_critical': pkg_name in self.CRITICAL_DEPS
                })
                
                if pkg_name in self.OPTIONAL_DEPS:
                    feature = self.OPTIONAL_DEPS[pkg_name].get('feature', '未知功能')
                    degradation = self.OPTIONAL_DEPS[pkg_name].get('graceful_degradation', '功能受限')
                    self.degraded_features.append(f"{feature} ({degradation})")
        
        return len(self.missing) == 0
    
    def install_missing(self, auto_confirm: bool = False, use_mirrors: bool = True) -> bool:
        """自动安装缺失的依赖"""
        if not self.missing:
            safe_print("[OK] 所有依赖已安装")
            return True
        
        critical_missing = [d for d in self.missing if d in self.CRITICAL_DEPS]
        optional_missing = [d for d in self.missing if d in self.OPTIONAL_DEPS]
        
        self._print_dependency_summary(critical_missing, optional_missing)
        
        if not auto_confirm:
            if not self._ask_install_permission(critical_missing, optional_missing):
                return False
        
        success = self._install_packages(self.missing, use_mirrors)
        
        if success:
            safe_print("\n验证安装结果...")
            recheck = DependencyManager()
            if recheck.check_all(include_optional=True):
                safe_print("[OK] 所有依赖验证通过")
                return True
            else:
                safe_print(f"[WARN] 仍有依赖未安装：{', '.join(recheck.missing)}")
                return False
        
        return False
    
    def _print_dependency_summary(self, critical: List[str], optional: List[str]):
        """打印依赖摘要"""
        safe_print("\n" + "="*70)
        safe_print("[PKG] 依赖检查报告")
        safe_print("="*70)
        
        if critical:
            safe_print(f"\n[CRITICAL] 关键依赖缺失 ({len(critical)}):")
            for pkg in critical:
                safe_print(f"   [ERROR] {pkg}")
            safe_print("   [WARN] 这些依赖是系统运行所必需的")
        
        if optional:
            safe_print(f"\n[WARNING] 可选依赖缺失 ({len(optional)}):")
            for pkg in optional:
                feature = self.OPTIONAL_DEPS.get(pkg, {}).get('feature', '未知功能')
                safe_print(f"   [WARN] {pkg} - {feature}")
            
            if self.degraded_features:
                safe_print(f"\n[DEGRADED] 受影响的特性:")
                for feature in self.degraded_features:
                    safe_print(f"   - {feature}")
        
        safe_print("\n" + "="*70)
    
    def _ask_install_permission(self, critical: List[str], optional: List[str]) -> bool:
        """询问用户是否安装"""
        if critical:
            safe_print("\n[IMPORTANT] 关键依赖缺失，系统无法正常运行")
            response = input("是否立即安装关键依赖？(Y/n): ").strip().lower()
            if response in ('n', 'no'):
                safe_print("[WARN] 跳过关键依赖安装，系统将无法启动")
                return False
        else:
            safe_print("\n[INFO] 可选依赖缺失，系统可降级运行")
            response = input("是否安装可选依赖以启用完整功能？(y/N): ").strip().lower()
            if response not in ('y', 'yes'):
                safe_print("[INFO] 系统将降级运行")
                return False
        
        return True
    
    def _install_packages(self, packages: List[str], use_mirrors: bool) -> bool:
        """安装指定的包"""
        safe_print(f"\n[FIX] 正在安装 {len(packages)} 个依赖包...")
        
        base_cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', '--quiet']
        
        for pkg in packages:
            if pkg in self.CRITICAL_DEPS:
                base_cmd.append(self.CRITICAL_DEPS[pkg]['package'])
            elif pkg in self.OPTIONAL_DEPS:
                base_cmd.append(self.OPTIONAL_DEPS[pkg]['package'])
            else:
                base_cmd.append(pkg)
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            safe_print(f"\n尝试 {attempt}/{max_retries}...")
            
            if use_mirrors and attempt > 1:
                mirror_idx = (attempt - 2) % len(self.MIRRORS)
                mirror_name, mirror_url = self.MIRRORS[mirror_idx]
                safe_print(f"使用 {mirror_name} 镜像源...")
                cmd = base_cmd + ['-i', mirror_url, '--trusted-host', mirror_url.split('/')[2]]
            else:
                cmd = base_cmd
            
            try:
                result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    safe_print("[OK] 依赖安装成功")
                    return True
                else:
                    safe_print(f"[ERROR] 安装失败：{result.stderr[:200]}")
                    
            except subprocess.TimeoutExpired:
                safe_print("[ERROR] 安装超时，请检查网络连接")
            except Exception as e:
                safe_print(f"[ERROR] 安装出错：{e}")
        
        safe_print("\n[IMPORTANT] 所有尝试均失败，请检查网络或手动安装")
        return False
    
    def get_installation_guide(self) -> str:
        """获取手动安装指南"""
        guide = []
        guide.append("\n" + "="*70)
        guide.append("[GUIDE] 依赖安装指南")
        guide.append("="*70)
        
        if not self.missing:
            guide.append("\n[OK] 所有依赖已安装")
            return "\n".join(guide)
        
        guide.append("\n方法 1: 使用自动修复（推荐）")
        guide.append("   python nuwactl.py repair --auto")
        
        guide.append("\n方法 2: 使用 requirements.txt")
        guide.append("   pip install -r requirements.txt")
        
        guide.append("\n方法 3: 手动安装单个包")
        for pkg in self.missing:
            if pkg in self.CRITICAL_DEPS:
                guide.append(f"   pip install {self.CRITICAL_DEPS[pkg]['package']}")
            elif pkg in self.OPTIONAL_DEPS:
                guide.append(f"   pip install {self.OPTIONAL_DEPS[pkg]['package']}")
        
        guide.append("\n方法 4: 使用安装脚本")
        if os.name == 'nt':
            guide.append("   install_deps_windows.bat")
        else:
            guide.append("   chmod +x install_deps_linux.sh && ./install_deps_linux.sh")
        
        guide.append("\n方法 5: 使用国内镜像加速")
        guide.append("   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
        
        guide.append("\n" + "="*70)
        return "\n".join(guide)
    
    def check_and_report(self, include_optional: bool = True) -> Tuple[bool, str]:
        """检查依赖并生成报告"""
        self.check_all(include_optional)
        
        report = []
        report.append("\n" + "="*70)
        report.append("依赖状态报告")
        report.append("="*70)
        
        installed_list = [pkg for pkg, ok in self.installed.items() if ok]
        if installed_list:
            report.append(f"\n已安装 ({len(installed_list)}):")
            for pkg in sorted(installed_list):
                report.append(f"   + {pkg}")
        
        if self.missing:
            report.append(f"\n缺失 ({len(self.missing)}):")
            for pkg in self.missing:
                is_critical = pkg in self.CRITICAL_DEPS
                marker = "[CRITICAL]" if is_critical else "[WARN]"
                report.append(f"   {marker} {pkg}")
        
        if self.degraded_features:
            report.append(f"\n降级特性:")
            for feature in self.degraded_features:
                report.append(f"   - {feature}")
        
        report.append("\n" + "="*70)
        
        all_ok = len(self.missing) == 0
        return all_ok, "\n".join(report)


def quick_check(auto_fix: bool = False) -> bool:
    """快速检查依赖"""
    manager = DependencyManager()
    all_ok = manager.check_all(include_optional=True)
    
    if all_ok:
        return True
    
    if auto_fix:
        return manager.install_missing(auto_confirm=True)
    else:
        safe_print(manager.get_installation_guide())
        return False


def ensure_dependencies(auto_fix: bool = False, quiet: bool = False) -> bool:
    """确保依赖已安装（主入口函数）"""
    if quiet:
        manager = DependencyManager()
        return manager.check_all(include_optional=True)
    
    manager = DependencyManager()
    all_ok = manager.check_all(include_optional=True)
    
    if all_ok:
        safe_print("[OK] 所有依赖检查通过")
        return True
    
    critical_missing = [d for d in manager.missing if d in manager.CRITICAL_DEPS]
    optional_missing = [d for d in manager.missing if d in manager.OPTIONAL_DEPS]
    
    if critical_missing:
        safe_print(f"\n[CRITICAL] 关键依赖缺失：{', '.join(critical_missing)}")
        safe_print("[WARN] 系统可能无法正常运行")
    else:
        safe_print(f"\n[WARN] 可选依赖缺失：{', '.join(optional_missing)}")
        safe_print("[INFO] 系统将降级运行")
    
    if auto_fix:
        safe_print("\n正在自动修复...")
        return manager.install_missing(auto_confirm=True, use_mirrors=True)
    else:
        safe_print(manager.get_installation_guide())
        
        if critical_missing:
            response = input("\n是否继续？(y/N): ").strip().lower()
            if response not in ('y', 'yes'):
                return False
    
    return True
