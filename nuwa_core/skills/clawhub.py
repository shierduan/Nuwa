import os
import subprocess
import json
from typing import List, Dict, Optional

class ClawHubManager:
    """ClawHub 技能管理类"""
    
    def __init__(self, skills_dir: Optional[str] = None):
        """初始化 ClawHub 管理器
        
        Args:
            skills_dir: 技能目录路径，默认为当前工作目录下的 skills 文件夹
        """
        self.skills_dir = skills_dir or os.path.join(os.getcwd(), 'skills')
    
    def _run_clawhub_command(self, args: List[str]) -> Dict:
        """运行 ClawHub 命令
        
        Args:
            args: 命令参数列表
            
        Returns:
            命令执行结果，包含 stdout、stderr 和 returncode
        """
        command = ['clawhub'] + args
        
        # 添加工作目录和技能目录参数
        if self.skills_dir:
            command.extend(['--workdir', os.path.dirname(self.skills_dir)])
            command.extend(['--dir', os.path.basename(self.skills_dir)])
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            shell=True  # 在 Windows 上需要使用 shell=True
        )
        
        return {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    
    def search(self, query: str) -> List[Dict]:
        """搜索技能
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果列表，每个元素是技能信息字典
        """
        result = self._run_clawhub_command(['search', query])
        
        if result['returncode'] != 0:
            print(f"搜索技能失败: {result['stderr']}")
            return []
        
        # 解析文本输出
        skills = []
        lines = result['stdout'].strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 解析每行的格式: slug  Name  (score)
            parts = line.split('  ')
            if len(parts) >= 3:
                slug = parts[0].strip()
                # 提取名称（可能包含空格）
                name_parts = parts[1:-1]
                name = ' '.join(name_parts).strip()
                # 提取分数
                score_str = parts[-1].strip()
                score = score_str.strip('()') if score_str.startswith('(') and score_str.endswith(')') else score_str
                
                skill = {
                    'slug': slug,
                    'name': name,
                    'score': score
                }
                skills.append(skill)
        
        return skills
    
    def install(self, skill_slug: str, version: Optional[str] = None) -> bool:
        """安装技能
        
        Args:
            skill_slug: 技能 slug
            version: 技能版本，可选
            
        Returns:
            安装是否成功
        """
        args = ['install', skill_slug]
        if version:
            args.extend(['--version', version])
        
        result = self._run_clawhub_command(args)
        
        if result['returncode'] != 0:
            # 检查是否是因为技能已经安装
            if "Already installed" in result['stderr']:
                print(f"技能已安装: {skill_slug}")
                return True
            else:
                print(f"安装技能失败: {result['stderr']}")
                return False
        
        print(f"安装技能成功: {result['stdout']}")
        return True
    
    def uninstall(self, skill_slug: str) -> bool:
        """卸载技能
        
        Args:
            skill_slug: 技能 slug
            
        Returns:
            卸载是否成功
        """
        result = self._run_clawhub_command(['uninstall', skill_slug])
        
        if result['returncode'] != 0:
            print(f"卸载技能失败: {result['stderr']}")
            return False
        
        print(f"卸载技能成功: {result['stdout']}")
        return True
    
    def list_installed(self) -> List[Dict]:
        """列出已安装的技能
        
        Returns:
            已安装技能列表
        """
        # 首先尝试使用 clawhub list 命令
        result = self._run_clawhub_command(['list'])
        
        if result['returncode'] == 0 and result['stdout']:
            # 解析文本输出
            skills = []
            lines = result['stdout'].strip().split('\n')
            
            current_skill = {}
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 检查是否是新技能的开始
                if line.startswith('┌') or line.startswith('├') or line.startswith('└'):
                    # 如果当前技能有内容，添加到列表
                    if current_skill:
                        skills.append(current_skill)
                        current_skill = {}
                elif ': ' in line:
                    # 解析键值对
                    key, value = line.split(': ', 1)
                    key = key.strip().lower()
                    if key == 'name':
                        current_skill['name'] = value
                    elif key == 'slug':
                        current_skill['slug'] = value
                    elif key == 'version':
                        current_skill['version'] = value
                    elif key == 'author':
                        current_skill['author'] = value
                    elif key == 'description':
                        current_skill['description'] = value
            
            # 添加最后一个技能
            if current_skill:
                skills.append(current_skill)
            
            if skills:
                return skills
        
        # 如果 clawhub list 命令失败或没有输出，直接检查技能目录
        skills = []
        if os.path.exists(self.skills_dir):
            for item in os.listdir(self.skills_dir):
                skill_dir = os.path.join(self.skills_dir, item)
                if os.path.isdir(skill_dir):
                    # 检查是否有 SKILL.md 文件
                    skill_md = os.path.join(skill_dir, 'SKILL.md')
                    if os.path.exists(skill_md):
                        try:
                            # 读取 SKILL.md 文件，提取技能信息
                            with open(skill_md, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # 解析 frontmatter
                            skill_info = {}
                            lines = content.strip().split('\n')
                            if lines and lines[0].strip() == '---':
                                frontmatter_end = -1
                                for i, line in enumerate(lines[1:], 1):
                                    if line.strip() == '---':
                                        frontmatter_end = i
                                        break
                                if frontmatter_end > 0:
                                    for line in lines[1:frontmatter_end]:
                                        line = line.strip()
                                        if ':' in line:
                                            key, value = line.split(':', 1)
                                            key = key.strip()
                                            value = value.strip().strip('"\'')
                                            if key == 'name':
                                                skill_info['name'] = value
                                            elif key == 'description':
                                                skill_info['description'] = value
                            
                            # 如果没有 frontmatter，使用目录名作为技能名
                            if 'name' not in skill_info:
                                skill_info['name'] = item
                            
                            skill_info['slug'] = item
                            skill_info['version'] = '1.0.0'  # 默认版本
                            skills.append(skill_info)
                        except Exception as e:
                            print(f"解析技能 {item} 失败: {e}")
        
        return skills
    
    def update(self, skill_slug: Optional[str] = None, version: Optional[str] = None) -> bool:
        """更新技能
        
        Args:
            skill_slug: 技能 slug，可选，不提供则更新所有技能
            version: 技能版本，可选
            
        Returns:
            更新是否成功
        """
        args = ['update']
        if skill_slug:
            args.append(skill_slug)
            if version:
                args.extend(['--version', version])
        
        result = self._run_clawhub_command(args)
        
        if result['returncode'] != 0:
            print(f"更新技能失败: {result['stderr']}")
            return False
        
        print(f"更新技能成功: {result['stdout']}")
        return True

# 全局 ClawHub 管理器实例
_clawhub_manager = None

def get_clawhub_manager(skills_dir: Optional[str] = None) -> ClawHubManager:
    """获取 ClawHub 管理器实例
    
    Args:
        skills_dir: 技能目录路径
        
    Returns:
        ClawHub 管理器实例
    """
    global _clawhub_manager
    if _clawhub_manager is None or (skills_dir and _clawhub_manager.skills_dir != skills_dir):
        _clawhub_manager = ClawHubManager(skills_dir)
    return _clawhub_manager

# 便捷函数
def search_skills(query: str) -> List[Dict]:
    """搜索技能
    
    Args:
        query: 搜索关键词
        
    Returns:
        搜索结果列表
    """
    return get_clawhub_manager().search(query)

def install_skill(skill_slug: str, version: Optional[str] = None) -> bool:
    """安装技能
    
    Args:
        skill_slug: 技能 slug
        version: 技能版本
        
    Returns:
        安装是否成功
    """
    return get_clawhub_manager().install(skill_slug, version)

def uninstall_skill(skill_slug: str) -> bool:
    """卸载技能
    
    Args:
        skill_slug: 技能 slug
        
    Returns:
        卸载是否成功
    """
    return get_clawhub_manager().uninstall(skill_slug)

def list_skills() -> List[Dict]:
    """列出已安装的技能
    
    Returns:
        已安装技能列表
    """
    return get_clawhub_manager().list_installed()

def update_skill(skill_slug: Optional[str] = None, version: Optional[str] = None) -> bool:
    """更新技能
    
    Args:
        skill_slug: 技能 slug
        version: 技能版本
        
    Returns:
        更新是否成功
    """
    return get_clawhub_manager().update(skill_slug, version)
