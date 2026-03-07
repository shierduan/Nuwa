import os
import importlib
import sys
from typing import Dict, List, Optional, Any, Callable
from .agent_skills import AgentSkill
from .clawhub import get_clawhub_manager
from .workspace import load_skill_entries, filter_skill_entries, build_workspace_skill_command_specs
from .skill_types import SkillEntry
from .web_fetch import web_fetch, search_web

class SkillManager:
    """技能管理器 - 统一管理ClawHub和AgentSkills"""
    
    def __init__(self, skills_dirs: Optional[List[str]] = None):
        """初始化技能管理器
        
        Args:
            skills_dirs: 技能目录路径列表
        """
        # 默认为当前工作目录下的skills文件夹和data/nuwa/skills文件夹
        default_dirs = [
            os.path.join(os.getcwd(), 'skills'),
            os.path.join(os.getcwd(), 'data', 'nuwa', 'skills')
        ]
        self.skills_dirs = skills_dirs or default_dirs
        # 过滤存在的目录
        self.skills_dirs = [d for d in self.skills_dirs if os.path.exists(d)]
        
        # 使用第一个目录作为ClawHub管理器的默认目录
        primary_skills_dir = self.skills_dirs[0] if self.skills_dirs else None
        self.clawhub_manager = get_clawhub_manager(primary_skills_dir)
        self.agent_skills = []
        self.clawhub_skills = []
        self.skill_executors = {}
        self._load_agent_skills()
        self._load_clawhub_skills()
        self._register_skill_executors()
    
    def _register_skill_executors(self):
        """注册技能执行器"""
        # 注册ClawHub技能执行器
        self.skill_executors['multi-search-engine'] = self._execute_multi_search_engine
    
    def _load_agent_skills(self):
        """加载AgentSkills"""
        # 从agent_skills.py中获取已注册的技能
        try:
            from .weather_skill import WeatherSkill
            self.agent_skills = [
                WeatherSkill()
            ]
        except ImportError:
            self.agent_skills = []
        
        # 尝试从所有技能目录加载自定义AgentSkills
        for skills_dir in self.skills_dirs:
            if os.path.exists(skills_dir):
                for item in os.listdir(skills_dir):
                    skill_dir = os.path.join(skills_dir, item)
                    if os.path.isdir(skill_dir):
                        # 检查是否有__init__.py文件
                        init_file = os.path.join(skill_dir, '__init__.py')
                        if os.path.exists(init_file):
                            try:
                                # 动态导入技能模块
                                module_name = f"nuwa_core.skills.custom.{item}"
                                spec = importlib.util.spec_from_file_location(module_name, init_file)
                                if spec and spec.loader:
                                    module = importlib.util.module_from_spec(spec)
                                    sys.modules[module_name] = module
                                    spec.loader.exec_module(module)
                                    
                                    # 查找继承自AgentSkill的类
                                    for name, obj in module.__dict__.items():
                                        if isinstance(obj, type) and issubclass(obj, AgentSkill) and obj != AgentSkill:
                                            try:
                                                skill_instance = obj()
                                                # 检查是否已存在同名技能
                                                if not any(s.name == skill_instance.name for s in self.agent_skills):
                                                    self.agent_skills.append(skill_instance)
                                            except Exception as e:
                                                print(f"加载AgentSkill {name} 失败: {e}")
                            except Exception as e:
                                print(f"导入技能模块 {item} 失败: {e}")
    
    def _load_clawhub_skills(self):
        """加载ClawHub技能"""
        all_skills = []
        seen_slugs = set()
        
        # 从所有技能目录加载ClawHub技能
        for skills_dir in self.skills_dirs:
            # 创建临时ClawHub管理器来加载当前目录的技能
            temp_manager = get_clawhub_manager(skills_dir)
            skills = temp_manager.list_installed()
            
            # 去重，使用slug作为唯一标识
            for skill in skills:
                slug = skill.get('slug', '')
                if slug and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    all_skills.append(skill)
        
        self.clawhub_skills = all_skills
    
    def get_all_skills(self) -> Dict[str, List[Any]]:
        """获取所有技能
        
        Returns:
            包含AgentSkills和ClawHub技能的字典
        """
        return {
            'agent_skills': self.agent_skills,
            'clawhub_skills': self.clawhub_skills
        }
    
    def get_agent_skills(self) -> List[AgentSkill]:
        """获取所有AgentSkills
        
        Returns:
            AgentSkill列表
        """
        return self.agent_skills
    
    def get_clawhub_skills(self) -> List[Dict]:
        """获取所有ClawHub技能
        
        Returns:
            ClawHub技能列表
        """
        return self.clawhub_skills
    
    def find_skill(self, query: str) -> Optional[Any]:
        """根据查询匹配适合的技能
        
        Args:
            query: 用户查询
            
        Returns:
            匹配的技能或None
        """
        query_lower = query.lower()
        
        # 首先尝试匹配AgentSkills
        for skill in self.agent_skills:
            if skill.can_handle(query):
                return skill
        
        # 然后尝试匹配ClawHub技能
        best_match = None
        best_score = 0
        
        for skill in self.clawhub_skills:
            skill_name = skill.get('name', '').lower()
            skill_description = skill.get('description', '').lower()
            
            score = 0
            
            # 1. 精确匹配技能名称
            if skill_name == query_lower:
                score = 100
            elif skill_name in query_lower:
                score = 80
            elif query_lower in skill_name:
                score = 70
            
            # 2. 关键词匹配
            skill_keywords = skill_name.replace('-', ' ').replace('_', ' ').split()
            if len(skill_keywords) > 0:
                matched_keywords = [kw for kw in skill_keywords if kw in query_lower and len(kw) > 2]
                if matched_keywords:
                    keyword_score = (len(matched_keywords) / len(skill_keywords)) * 60
                    score = max(score, keyword_score)
            
            # 3. 描述匹配
            if skill_description and any(kw in query_lower for kw in skill_description.split() if len(kw) > 2):
                score = max(score, 40)
            
            # 4. 特殊技能逻辑
            if skill_name == 'find-skills':
                if any(kw in query_lower for kw in ['find skill', 'install skill', '找技能', '安装技能']):
                    score = max(score, 90)
            
            if skill_name == 'multi-search-engine':
                if any(kw in query_lower for kw in ['search', '访问网站', '查询', 'baidu', 'google', '搜索', 'website', 'url']):
                    score = max(score, 90)
            
            # 更新最佳匹配
            if score > best_score:
                best_score = score
                best_match = skill
        
        # 只有当匹配分数超过阈值时才返回匹配结果
        if best_score >= 40:
            return best_match
        
        return None
    
    async def execute_skill(self, skill: Any, query: str, emotion_state: Dict[str, float], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能
        
        Args:
            skill: 技能实例
            query: 用户查询
            emotion_state: 当前情绪状态
            memory_context: 记忆上下文
            
        Returns:
            技能执行结果
        """
        if isinstance(skill, AgentSkill):
            # 执行AgentSkill
            return await skill.execute(query, emotion_state, memory_context)
        elif isinstance(skill, dict) and 'slug' in skill:
            # 执行ClawHub技能
            skill_name = skill.get('name', '').lower()
            if skill_name in self.skill_executors:
                return await self.skill_executors[skill_name](skill, query, emotion_state, memory_context)
            else:
                return {
                    'success': False,
                    'result': {},
                    'emotion_update': {},
                    'memory_update': '',
                    'message': f"ClawHub技能 {skill['name']} 执行功能正在开发中"
                }
        else:
            return {
                'success': False,
                'result': {},
                'emotion_update': {},
                'memory_update': '',
                'message': "未知技能类型"
            }
    
    async def _execute_multi_search_engine(self, skill: Dict, query: str, emotion_state: Dict[str, float], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行multi-search-engine技能"""
        import re
        url_pattern = r'(https?://)?(www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})(/[^\s]*)?'
        urls = re.findall(url_pattern, query)
        domain_pattern = r'(baidu|google|bing|github|stackoverflow)\.com'
        domains = re.findall(domain_pattern, query.lower())
        
        if urls or domains:
            target_url = urls[0][2] if urls else (domains[0] + '.com' if domains else '')
            if not target_url.startswith('http'):
                target_url = 'https://' + target_url
            
            # 实际执行网页抓取
            fetch_result = await web_fetch({'url': target_url})
            if fetch_result['success']:
                data = fetch_result['data']
                title = data.get('title', '未知页面')
                description = data.get('description', '无描述')
                content = data.get('content', '无内容')[:200] + '...' if data.get('content') else '无内容'
                
                return {
                    "success": True,
                    "result": {"skill_name": skill.get('name'), "description": skill.get('description'), "target_url": target_url, "page_info": {"title": title, "description": description}},
                    "emotion_update": {"joy": 0.1, "anticipation": 0.1},
                    "memory_update": f"使用 multi-search-engine 访问了 {target_url}，页面标题: {title}",
                    "message": f"我已经使用 multi-search-engine 技能访问了 {target_url}。\n\n页面标题: {title}\n描述: {description}\n\n内容摘要: {content}"
                }
            else:
                return {
                    "success": False,
                    "result": {"skill_name": skill.get('name'), "description": skill.get('description'), "target_url": target_url},
                    "emotion_update": {"sadness": 0.1},
                    "memory_update": f"使用 multi-search-engine 访问 {target_url} 失败",
                    "message": f"访问 {target_url} 失败: {fetch_result['message']}"
                }
        else:
            # 搜索模式
            search_query = query.lower().replace('search', '').replace('搜索', '').strip()
            if search_query:
                # 使用Google搜索
                search_result = await search_web(search_query, engine='google')
                if search_result['success']:
                    return {
                        "success": True,
                        "result": {"skill_name": skill.get('name'), "description": skill.get('description'), "search_query": search_query},
                        "emotion_update": {"joy": 0.1, "anticipation": 0.1},
                        "memory_update": f"使用 multi-search-engine 搜索了 '{search_query}'",
                        "message": f"我已经使用 multi-search-engine 技能搜索了 '{search_query}'。\n\n搜索结果: {search_result['data'].get('title', '无结果')}"
                    }
                else:
                    return {
                        "success": False,
                        "result": {"skill_name": skill.get('name'), "description": skill.get('description'), "search_query": search_query},
                        "emotion_update": {"sadness": 0.1},
                        "memory_update": f"使用 multi-search-engine 搜索 '{search_query}' 失败",
                        "message": f"搜索失败: {search_result['message']}"
                    }
            else:
                return {
                    "success": True,
                    "result": {"skill_name": skill.get('name'), "description": skill.get('description')},
                    "emotion_update": {"joy": 0.05},
                    "memory_update": f"使用了 {skill.get('name')} 技能进行搜索",
                    "message": f"我可以使用 multi-search-engine 技能帮你搜索信息。你想访问哪个网站或搜索什么内容？支持百度、谷歌、必应等 17 个搜索引擎。"
                }
    
    def search_skills(self, query: str) -> List[Dict]:
        """搜索技能
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果列表
        """
        # 搜索ClawHub技能
        clawhub_results = self.clawhub_manager.search(query)
        
        # 搜索AgentSkills
        agent_results = []
        for skill in self.agent_skills:
            if query.lower() in skill.name.lower() or any(query.lower() in keyword.lower() for keyword in skill.keywords):
                agent_results.append({
                    'name': skill.name,
                    'description': skill.description,
                    'type': 'agent_skill'
                })
        
        # 合并结果
        return agent_results + [{'type': 'clawhub_skill', **skill} for skill in clawhub_results]
    
    def install_skill(self, skill_slug: str, version: Optional[str] = None) -> bool:
        """安装技能
        
        Args:
            skill_slug: 技能slug
            version: 技能版本
            
        Returns:
            安装是否成功
        """
        result = self.clawhub_manager.install(skill_slug, version)
        if result:
            # 重新加载ClawHub技能
            self._load_clawhub_skills()
        return result
    
    def uninstall_skill(self, skill_slug: str) -> bool:
        """卸载技能
        
        Args:
            skill_slug: 技能slug
            
        Returns:
            卸载是否成功
        """
        result = self.clawhub_manager.uninstall(skill_slug)
        if result:
            # 重新加载ClawHub技能
            self._load_clawhub_skills()
        return result
    
    def update_skill(self, skill_slug: Optional[str] = None, version: Optional[str] = None) -> bool:
        """更新技能
        
        Args:
            skill_slug: 技能slug
            version: 技能版本
            
        Returns:
            更新是否成功
        """
        result = self.clawhub_manager.update(skill_slug, version)
        if result:
            # 重新加载ClawHub技能
            self._load_clawhub_skills()
        return result
    
    def get_skill_metadata(self) -> List[Dict[str, Any]]:
        """获取所有技能的元数据
        
        Returns:
            技能元数据列表
        """
        # 获取AgentSkills元数据
        agent_metadata = [skill.get_metadata() for skill in self.agent_skills]
        
        # 获取ClawHub技能元数据
        clawhub_metadata = self.clawhub_skills
        
        # 合并结果
        return agent_metadata + clawhub_metadata
    
    def reload_skills(self):
        """重新加载所有技能"""
        self._load_agent_skills()
        self._load_clawhub_skills()

# 全局技能管理器实例
_skill_manager = None

def get_skill_manager(skills_dirs: Optional[List[str]] = None) -> SkillManager:
    """获取技能管理器实例
    
    Args:
        skills_dirs: 技能目录路径列表
        
    Returns:
        技能管理器实例
    """
    global _skill_manager
    if _skill_manager is None or (skills_dirs and _skill_manager.skills_dirs != skills_dirs):
        _skill_manager = SkillManager(skills_dirs)
    return _skill_manager

# 便捷函数
def get_all_skills() -> Dict[str, List[Any]]:
    """获取所有技能
    
    Returns:
        包含AgentSkills和ClawHub技能的字典
    """
    return get_skill_manager().get_all_skills()

def find_skill(query: str) -> Optional[Any]:
    """根据查询匹配适合的技能
    
    Args:
        query: 用户查询
        
    Returns:
        匹配的技能或None
    """
    return get_skill_manager().find_skill(query)

async def execute_skill(skill: Any, query: str, emotion_state: Dict[str, float], memory_context: Dict[str, Any]) -> Dict[str, Any]:
    """执行技能
    
    Args:
        skill: 技能实例
        query: 用户查询
        emotion_state: 当前情绪状态
        memory_context: 记忆上下文
        
    Returns:
        技能执行结果
    """
    return await get_skill_manager().execute_skill(skill, query, emotion_state, memory_context)

def search_skills(query: str) -> List[Dict]:
    """搜索技能
    
    Args:
        query: 搜索关键词
        
    Returns:
        搜索结果列表
    """
    return get_skill_manager().search_skills(query)

def install_skill(skill_slug: str, version: Optional[str] = None) -> bool:
    """安装技能
    
    Args:
        skill_slug: 技能slug
        version: 技能版本
        
    Returns:
        安装是否成功
    """
    return get_skill_manager().install_skill(skill_slug, version)

def uninstall_skill(skill_slug: str) -> bool:
    """卸载技能
    
    Args:
        skill_slug: 技能slug
        
    Returns:
        卸载是否成功
    """
    return get_skill_manager().uninstall_skill(skill_slug)

def update_skill(skill_slug: Optional[str] = None, version: Optional[str] = None) -> bool:
    """更新技能
    
    Args:
        skill_slug: 技能slug
        version: 技能版本
        
    Returns:
        更新是否成功
    """
    return get_skill_manager().update_skill(skill_slug, version)

def get_skill_metadata() -> List[Dict[str, Any]]:
    """获取所有技能的元数据
    
    Returns:
        技能元数据列表
    """
    return get_skill_manager().get_skill_metadata()

def reload_skills():
    """重新加载所有技能"""
    get_skill_manager().reload_skills()
