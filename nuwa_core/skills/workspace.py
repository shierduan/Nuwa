import os
import re
import json
from typing import Any, Dict, List, Optional, Set
from .skill_types import SkillEntry, SkillCard, SkillSnapshot, SkillEligibilityContext
from .frontmatter import parse_frontmatter, resolve_open_claw_metadata, resolve_skill_invocation_policy
from .clawhub import search_skills, install_skill, uninstall_skill, list_skills, update_skill
from .agent_skills import AgentSkill

# 常量定义
SKILL_COMMAND_MAX_LENGTH = 32
SKILL_COMMAND_FALLBACK = "skill"
SKILL_COMMAND_DESCRIPTION_MAX_LENGTH = 100

DEFAULT_MAX_CANDIDATES_PER_ROOT = 300
DEFAULT_MAX_SKILLS_LOADED_PER_SOURCE = 200
DEFAULT_MAX_SKILLS_IN_PROMPT = 150
DEFAULT_MAX_SKILLS_PROMPT_CHARS = 30000
DEFAULT_MAX_SKILL_FILE_BYTES = 256000

def compact_skill_paths(skills: List[Dict]) -> List[Dict]:
    """替换技能文件路径中的用户主目录前缀为~，减少系统提示令牌使用"""
    home = os.path.expanduser("~")
    if not home:
        return skills
    prefix = home if home.endswith(os.sep) else home + os.sep
    for skill in skills:
        if 'filePath' in skill and skill['filePath'].startswith(prefix):
            skill['filePath'] = '~/' + skill['filePath'][len(prefix):]
    return skills

def sanitize_skill_command_name(raw: str) -> str:
    """清理技能命令名称"""
    normalized = re.sub(r'[^a-z0-9_]+', '_', raw.lower())
    normalized = re.sub(r'_+', '_', normalized)
    normalized = re.sub(r'^_|_$', '', normalized)
    trimmed = normalized[:SKILL_COMMAND_MAX_LENGTH]
    return trimmed or SKILL_COMMAND_FALLBACK

def resolve_unique_skill_command_name(base: str, used: Set[str]) -> str:
    """解析唯一的技能命令名称"""
    normalized_base = base.lower()
    if normalized_base not in used:
        return base
    for index in range(2, 1000):
        suffix = f"_{index}"
        max_base_length = max(1, SKILL_COMMAND_MAX_LENGTH - len(suffix))
        trimmed_base = base[:max_base_length]
        candidate = f"{trimmed_base}{suffix}"
        candidate_key = candidate.lower()
        if candidate_key not in used:
            return candidate
    fallback = f"{base[:max(1, SKILL_COMMAND_MAX_LENGTH - 2)]}_x"
    return fallback

def resolve_skills_limits(config: Optional[Dict] = None) -> Dict:
    """解析技能限制配置"""
    limits = config.get('skills', {}).get('limits', {}) if config else {}
    return {
        'maxCandidatesPerRoot': limits.get('maxCandidatesPerRoot', DEFAULT_MAX_CANDIDATES_PER_ROOT),
        'maxSkillsLoadedPerSource': limits.get('maxSkillsLoadedPerSource', DEFAULT_MAX_SKILLS_LOADED_PER_SOURCE),
        'maxSkillsInPrompt': limits.get('maxSkillsInPrompt', DEFAULT_MAX_SKILLS_IN_PROMPT),
        'maxSkillsPromptChars': limits.get('maxSkillsPromptChars', DEFAULT_MAX_SKILLS_PROMPT_CHARS),
        'maxSkillFileBytes': limits.get('maxSkillFileBytes', DEFAULT_MAX_SKILL_FILE_BYTES)
    }

def list_child_directories(dir_path: str) -> List[str]:
    """列出子目录"""
    try:
        entries = os.listdir(dir_path)
        dirs = []
        for entry in entries:
            if entry.startswith('.') or entry == 'node_modules':
                continue
            full_path = os.path.join(dir_path, entry)
            if os.path.isdir(full_path):
                dirs.append(entry)
            elif os.path.islink(full_path):
                try:
                    if os.path.isdir(os.path.realpath(full_path)):
                        dirs.append(entry)
                except:
                    pass
        return dirs
    except:
        return []

def resolve_nested_skills_root(dir_path: str, opts: Optional[Dict] = None) -> Dict:
    """解析嵌套的技能根目录"""
    nested = os.path.join(dir_path, 'skills')
    try:
        if not os.path.exists(nested) or not os.path.isdir(nested):
            return {'baseDir': dir_path}
    except:
        return {'baseDir': dir_path}
    
    # 启发式：如果存在dir/skills/*/SKILL.md，则将dir/skills视为真正的根目录
    nested_dirs = list_child_directories(nested)
    scan_limit = max(0, opts.get('maxEntriesToScan', 100) if opts else 100)
    to_scan = nested_dirs[:min(len(nested_dirs), scan_limit)] if scan_limit > 0 else []
    
    for name in to_scan:
        skill_md = os.path.join(nested, name, 'SKILL.md')
        if os.path.exists(skill_md):
            return {'baseDir': nested, 'note': f'Detected nested skills root at {nested}'}
    return {'baseDir': dir_path}

def unwrap_loaded_skills(loaded: any) -> List[Dict]:
    """解包加载的技能"""
    if isinstance(loaded, list):
        return loaded
    if isinstance(loaded, dict) and 'skills' in loaded:
        skills = loaded['skills']
        if isinstance(skills, list):
            return skills
    return []

def load_skill_entries(workspace_dir: str, opts: Optional[Dict] = None) -> List[SkillEntry]:
    """加载技能条目"""
    config = opts.get('config') if opts else None
    limits = resolve_skills_limits(config)
    
    def load_skills(params: Dict) -> List[Dict]:
        """加载技能"""
        resolved = resolve_nested_skills_root(params['dir'], {
            'maxEntriesToScan': limits['maxCandidatesPerRoot']
        })
        base_dir = resolved['baseDir']
        
        # 如果根目录本身是技能目录，直接加载
        root_skill_md = os.path.join(base_dir, 'SKILL.md')
        if os.path.exists(root_skill_md):
            try:
                size = os.path.getsize(root_skill_md)
                if size > limits['maxSkillFileBytes']:
                    print(f"Skipping skills root due to oversized SKILL.md: {root_skill_md}")
                    return []
            except:
                return []
            
            # 简单实现：从SKILL.md文件中读取技能信息
            try:
                with open(root_skill_md, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 提取技能名称和描述
                name = os.path.basename(base_dir)
                description = ""
                # 解析SKILL.md内容，支持frontmatter格式
                lines = content.strip().split('\n')
                if lines:
                    # 检查是否有frontmatter
                    if lines[0].strip() == '---':
                        # 解析frontmatter
                        frontmatter_end = -1
                        for i, line in enumerate(lines[1:], 1):
                            if line.strip() == '---':
                                frontmatter_end = i
                                break
                        if frontmatter_end > 0:
                            # 解析frontmatter内容
                            for line in lines[1:frontmatter_end]:
                                line = line.strip()
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    key = key.strip()
                                    value = value.strip().strip('"\'')
                                    if key == 'name':
                                        name = value
                                    elif key == 'description':
                                        description = value
                            # 寻找描述（如果frontmatter中没有）
                            if not description and frontmatter_end + 1 < len(lines):
                                for line in lines[frontmatter_end + 1:]:
                                    line = line.strip()
                                    if line and not line.startswith('#'):
                                        description = line
                                        break
                    else:
                        # 普通格式，第一行是名称
                        if lines[0].strip():
                            name = lines[0].strip()
                        # 寻找描述
                        for line in lines[1:]:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                description = line
                                break
                # 创建技能字典
                skill = {
                    'name': name,
                    'description': description,
                    'filePath': root_skill_md,
                    'baseDir': base_dir
                }
                return [skill]
            except:
                return []
        
        child_dirs = list_child_directories(base_dir)
        suspicious = len(child_dirs) > limits['maxCandidatesPerRoot']
        
        max_candidates = max(0, limits['maxSkillsLoadedPerSource'])
        limited_children = sorted(child_dirs)[:max_candidates]
        
        if suspicious:
            print(f"Skills root looks suspiciously large, truncating discovery: {params['dir']}")
        elif len(child_dirs) > max_candidates:
            print(f"Skills root has many entries, truncating discovery: {params['dir']}")
        
        loaded_skills = []
        
        # 只考虑看起来像技能的直接子文件夹（有SKILL.md）且在大小限制内
        for name in limited_children:
            skill_dir = os.path.join(base_dir, name)
            skill_md = os.path.join(skill_dir, 'SKILL.md')
            if not os.path.exists(skill_md):
                continue
            try:
                size = os.path.getsize(skill_md)
                if size > limits['maxSkillFileBytes']:
                    print(f"Skipping skill due to oversized SKILL.md: {name}")
                    continue
            except:
                continue
            
            # 简单实现：从SKILL.md文件中读取技能信息
            try:
                with open(skill_md, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 提取技能名称和描述
                name = os.path.basename(skill_dir)
                description = ""
                # 解析SKILL.md内容，支持frontmatter格式
                lines = content.strip().split('\n')
                if lines:
                    # 检查是否有frontmatter
                    if lines[0].strip() == '---':
                        # 解析frontmatter
                        frontmatter_end = -1
                        for i, line in enumerate(lines[1:], 1):
                            if line.strip() == '---':
                                frontmatter_end = i
                                break
                        if frontmatter_end > 0:
                            # 解析frontmatter内容
                            for line in lines[1:frontmatter_end]:
                                line = line.strip()
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    key = key.strip()
                                    value = value.strip().strip('"\'')
                                    if key == 'name':
                                        name = value
                                    elif key == 'description':
                                        description = value
                            # 寻找描述（如果frontmatter中没有）
                            if not description and frontmatter_end + 1 < len(lines):
                                for line in lines[frontmatter_end + 1:]:
                                    line = line.strip()
                                    if line and not line.startswith('#'):
                                        description = line
                                        break
                    else:
                        # 普通格式，第一行是名称
                        if lines[0].strip():
                            name = lines[0].strip()
                        # 寻找描述
                        for line in lines[1:]:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                description = line
                                break
                # 创建技能字典
                skill = {
                    'name': name,
                    'description': description,
                    'filePath': skill_md,
                    'baseDir': skill_dir
                }
                loaded_skills.append(skill)
            except:
                pass
            
            if len(loaded_skills) >= limits['maxSkillsLoadedPerSource']:
                break
        
        if len(loaded_skills) > limits['maxSkillsLoadedPerSource']:
            return sorted(loaded_skills, key=lambda s: s['name'])[:limits['maxSkillsLoadedPerSource']]
        
        return loaded_skills
    
    # 技能目录路径
    managed_skills_dir = opts.get('managedSkillsDir') if opts else os.path.join(os.path.expanduser('~'), '.nuwa', 'skills')
    workspace_skills_dir = os.path.join(workspace_dir, 'skills')
    bundled_skills_dir = opts.get('bundledSkillsDir') if opts else None
    extra_dirs_raw = config.get('skills', {}).get('load', {}).get('extraDirs', []) if config else []
    extra_dirs = [d.strip() for d in extra_dirs_raw if isinstance(d, str) and d.strip()]
    
    # 加载技能
    bundled_skills = load_skills({'dir': bundled_skills_dir, 'source': 'nuwa-bundled'}) if bundled_skills_dir else []
    extra_skills = []
    for dir_path in extra_dirs:
        resolved = os.path.expanduser(dir_path)
        extra_skills.extend(load_skills({'dir': resolved, 'source': 'nuwa-extra'}))
    managed_skills = load_skills({'dir': managed_skills_dir, 'source': 'nuwa-managed'})
    personal_agents_skills_dir = os.path.join(os.path.expanduser('~'), '.agents', 'skills')
    personal_agents_skills = load_skills({'dir': personal_agents_skills_dir, 'source': 'agents-skills-personal'})
    project_agents_skills_dir = os.path.join(workspace_dir, '.agents', 'skills')
    project_agents_skills = load_skills({'dir': project_agents_skills_dir, 'source': 'agents-skills-project'})
    workspace_skills = load_skills({'dir': workspace_skills_dir, 'source': 'nuwa-workspace'})
    
    # 合并技能，优先级：extra < bundled < managed < agents-skills-personal < agents-skills-project < workspace
    merged = {}
    for skill in extra_skills:
        merged[skill['name']] = skill
    for skill in bundled_skills:
        merged[skill['name']] = skill
    for skill in managed_skills:
        merged[skill['name']] = skill
    for skill in personal_agents_skills:
        merged[skill['name']] = skill
    for skill in project_agents_skills:
        merged[skill['name']] = skill
    for skill in workspace_skills:
        merged[skill['name']] = skill
    
    # 创建技能条目
    skill_entries = []
    for skill in merged.values():
        frontmatter = {}
        try:
            if 'filePath' in skill and os.path.exists(skill['filePath']):
                with open(skill['filePath'], 'r', encoding='utf-8') as f:
                    raw = f.read()
                    frontmatter = parse_frontmatter(raw)
        except:
            pass
        
        metadata = resolve_open_claw_metadata(frontmatter)
        invocation = resolve_skill_invocation_policy(frontmatter)
        
        # 创建技能卡
        card = None
        if metadata and metadata.card:
            card = SkillCard(
                name=skill['name'],
                title=metadata.card.get('title') or skill['name'],
                description=metadata.card.get('description') or skill.get('description'),
                emoji=metadata.emoji,
                icon=metadata.card.get('icon'),
                category=metadata.card.get('category'),
                tags=metadata.card.get('tags') or [],
                color=metadata.card.get('color'),
                background_color=metadata.card.get('backgroundColor')
            )
        else:
            # 为没有卡元数据的技能创建回退卡
            card = SkillCard(
                name=skill['name'],
                title=skill['name'],
                description=skill.get('description'),
                emoji=metadata.emoji if metadata else None
            )
        
        skill_entries.append(SkillEntry(
            skill=skill,
            frontmatter=frontmatter,
            metadata=metadata,
            invocation=invocation,
            card=card
        ))
    
    return skill_entries

def filter_skill_entries(entries: List[SkillEntry], config: Optional[Dict] = None, 
                        skill_filter: Optional[List[str]] = None, 
                        eligibility: Optional[SkillEligibilityContext] = None) -> List[SkillEntry]:
    """过滤技能条目"""
    # 这里需要实现shouldIncludeSkill函数，暂时返回所有条目
    # filtered = [entry for entry in entries if shouldIncludeSkill({'entry': entry, 'config': config, 'eligibility': eligibility})]
    filtered = entries
    
    # 如果提供了skillFilter，只包含过滤列表中的技能
    if skill_filter is not None:
        normalized = [skill.lower() for skill in skill_filter] if skill_filter else []
        label = ', '.join(normalized) if normalized else '(none)'
        print(f"Applying skill filter: {label}")
        filtered = [entry for entry in filtered if entry.skill['name'].lower() in normalized] if normalized else []
        filtered_names = [entry.skill['name'] for entry in filtered]
        print(f"After skill filter: {', '.join(filtered_names) or '(none)'}")
    
    return filtered

def apply_skills_prompt_limits(params: Dict) -> Dict:
    """应用技能提示限制"""
    skills = params.get('skills', [])
    config = params.get('config')
    limits = resolve_skills_limits(config)
    total = len(skills)
    by_count = skills[:max(0, limits['maxSkillsInPrompt'])]
    
    skills_for_prompt = by_count
    truncated = total > len(by_count)
    truncated_reason = 'count' if truncated else None
    
    def fits(skills_list: List[Dict]) -> bool:
        """检查技能是否适合提示"""
        # 这里需要实现formatSkillsForPrompt函数，暂时返回True
        # block = formatSkillsForPrompt(skills_list)
        # return len(block) <= limits['maxSkillsPromptChars']
        return True
    
    if not fits(skills_for_prompt):
        # 二分查找适合字符预算的最大前缀
        lo = 0
        hi = len(skills_for_prompt)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if fits(skills_for_prompt[:mid]):
                lo = mid
            else:
                hi = mid - 1
        skills_for_prompt = skills_for_prompt[:lo]
        truncated = True
        truncated_reason = 'chars'
    
    return {
        'skillsForPrompt': skills_for_prompt,
        'truncated': truncated,
        'truncatedReason': truncated_reason
    }

def build_workspace_skill_snapshot(workspace_dir: str, opts: Optional[Dict] = None) -> SkillSnapshot:
    """构建工作区技能快照"""
    # 这里需要实现resolveWorkspaceSkillPromptState函数，暂时返回空快照
    # state = resolveWorkspaceSkillPromptState(workspace_dir, opts)
    # skill_filter = normalizeSkillFilter(opts.get('skillFilter') if opts else None)
    # return SkillSnapshot(
    #     prompt=state['prompt'],
    #     skills=[{'name': entry.skill['name'], 'primaryEnv': entry.metadata.primary_env, 'requiredEnv': entry.metadata.requires.get('env')} for entry in state['eligible']],
    #     skill_filter=skill_filter,
    #     resolved_skills=state['resolvedSkills'],
    #     version=opts.get('snapshotVersion') if opts else None
    # )
    return SkillSnapshot()

def build_workspace_skills_prompt(workspace_dir: str, opts: Optional[Dict] = None) -> str:
    """构建工作区技能提示"""
    # 这里需要实现resolveWorkspaceSkillPromptState函数，暂时返回空字符串
    # state = resolveWorkspaceSkillPromptState(workspace_dir, opts)
    # return state['prompt']
    return ''

def resolve_skills_prompt_for_run(params: Dict) -> str:
    """解析运行的技能提示"""
    skills_snapshot = params.get('skillsSnapshot')
    if skills_snapshot and skills_snapshot.prompt:
        return skills_snapshot.prompt
    entries = params.get('entries')
    if entries and len(entries) > 0:
        prompt = build_workspace_skills_prompt(params.get('workspaceDir'), {
            'entries': entries,
            'config': params.get('config')
        })
        return prompt.strip() if prompt else ''
    return ''

def load_workspace_skill_entries(workspace_dir: str, opts: Optional[Dict] = None) -> List[SkillEntry]:
    """加载工作区技能条目"""
    return load_skill_entries(workspace_dir, opts)

def build_workspace_skill_cards(workspace_dir: str, opts: Optional[Dict] = None) -> List[SkillCard]:
    """构建工作区技能卡"""
    skill_entries = opts.get('entries') if opts else load_skill_entries(workspace_dir, opts)
    eligible = filter_skill_entries(
        skill_entries,
        opts.get('config') if opts else None,
        opts.get('skillFilter') if opts else None,
        opts.get('eligibility') if opts else None
    )
    return [entry.card for entry in eligible if entry.card]

def build_workspace_skill_cards_by_category(workspace_dir: str, opts: Optional[Dict] = None) -> Dict[str, List[SkillCard]]:
    """按类别构建工作区技能卡"""
    cards = build_workspace_skill_cards(workspace_dir, opts)
    categories = {}
    
    for card in cards:
        category = card.category or "Uncategorized"
        if category not in categories:
            categories[category] = []
        categories[category].append(card)
    
    # 对类别和每个类别中的卡进行排序
    for category in categories:
        categories[category].sort(key=lambda x: x.title or x.name)
    
    return categories

def build_workspace_skill_command_specs(workspace_dir: str, opts: Optional[Dict] = None) -> List[Dict]:
    """构建工作区技能命令规范"""
    from skill_types import SkillCommandSpec, SkillCommandDispatchSpec
    
    skill_entries = opts.get('entries') if opts else load_skill_entries(workspace_dir, opts)
    eligible = filter_skill_entries(
        skill_entries,
        opts.get('config') if opts else None,
        opts.get('skillFilter') if opts else None,
        opts.get('eligibility') if opts else None
    )
    user_invocable = [entry for entry in eligible if (entry.invocation and entry.invocation.user_invocable) or (not entry.invocation)]
    used = set()
    if opts and 'reservedNames' in opts:
        for reserved in opts['reservedNames']:
            used.add(reserved.lower())
    
    specs = []
    for entry in user_invocable:
        raw_name = entry.skill['name']
        base = sanitize_skill_command_name(raw_name)
        if base != raw_name:
            print(f'Sanitized skill command name "{raw_name}" to "/{base}"')
        unique = resolve_unique_skill_command_name(base, used)
        if unique != base:
            print(f'De-duplicated skill command name for "{raw_name}" to "/{unique}"')
        used.add(unique.lower())
        raw_description = entry.skill.get('description', '').strip() or raw_name
        description = raw_description[:SKILL_COMMAND_DESCRIPTION_MAX_LENGTH-1] + "…" if len(raw_description) > SKILL_COMMAND_DESCRIPTION_MAX_LENGTH else raw_description
        
        # 解析dispatch
        dispatch = None
        frontmatter = entry.frontmatter
        if frontmatter:
            kind_raw = (frontmatter.get('command-dispatch') or frontmatter.get('command_dispatch') or '').strip().lower()
            if kind_raw == 'tool':
                tool_name = (frontmatter.get('command-tool') or frontmatter.get('command_tool') or '').strip()
                if tool_name:
                    arg_mode_raw = (frontmatter.get('command-arg-mode') or frontmatter.get('command_arg_mode') or '').strip().lower()
                    arg_mode = 'raw' if not arg_mode_raw or arg_mode_raw == 'raw' else None
                    if not arg_mode:
                        print(f"Skill command \"/{unique}\" requested tool dispatch but has unknown command-arg-mode. Falling back to raw.")
                    dispatch = SkillCommandDispatchSpec(
                        kind='tool',
                        tool_name=tool_name,
                        arg_mode='raw'
                    )
                else:
                    print(f"Skill command \"/{unique}\" requested tool dispatch but did not provide command-tool. Ignoring dispatch.")
        
        # 包含卡元数据到命令规范
        card_metadata = None
        if entry.card:
            card_metadata = {
                'title': entry.card.title,
                'description': entry.card.description,
                'emoji': entry.card.emoji,
                'icon': entry.card.icon,
                'category': entry.card.category,
                'tags': entry.card.tags,
                'color': entry.card.color,
                'backgroundColor': entry.card.background_color
            }
        
        spec = SkillCommandSpec(
            name=unique,
            skill_name=raw_name,
            description=description,
            dispatch=dispatch,
            card=card_metadata
        )
        specs.append(spec.__dict__)
    
    return specs

def resolve_unique_synced_skill_dir_name(base: str, used: Set[str]) -> str:
    """解析唯一的同步技能目录名称"""
    if base not in used:
        used.add(base)
        return base
    for index in range(2, 10000):
        candidate = f"{base}-{index}"
        if candidate not in used:
            used.add(candidate)
            return candidate
    fallback_index = 10000
    fallback = f"{base}-{fallback_index}"
    while fallback in used:
        fallback_index += 1
        fallback = f"{base}-{fallback_index}"
    used.add(fallback)
    return fallback

def resolve_synced_skill_destination_path(params: Dict) -> str:
    """解析同步技能的目标路径"""
    target_skills_dir = params['targetSkillsDir']
    entry = params['entry']
    used_dir_names = params['usedDirNames']
    
    source_dir_name = os.path.basename(entry.skill.get('baseDir', '')).strip()
    if not source_dir_name or source_dir_name in ['.', '..']:
        return None
    
    unique_dir_name = resolve_unique_synced_skill_dir_name(source_dir_name, used_dir_names)
    return os.path.join(target_skills_dir, unique_dir_name)

import shutil

def sync_skills_to_workspace(params: Dict):
    """同步技能到工作区"""
    source_workspace_dir = params['sourceWorkspaceDir']
    target_workspace_dir = params['targetWorkspaceDir']
    config = params.get('config')
    managed_skills_dir = params.get('managedSkillsDir')
    bundled_skills_dir = params.get('bundledSkillsDir')
    
    source_dir = os.path.expanduser(source_workspace_dir)
    target_dir = os.path.expanduser(target_workspace_dir)
    if source_dir == target_dir:
        return
    
    target_skills_dir = os.path.join(target_dir, 'skills')
    
    # 加载技能条目
    entries = load_skill_entries(source_dir, {
        'config': config,
        'managedSkillsDir': managed_skills_dir,
        'bundledSkillsDir': bundled_skills_dir
    })
    
    # 清理目标技能目录
    if os.path.exists(target_skills_dir):
        shutil.rmtree(target_skills_dir)
    os.makedirs(target_skills_dir, exist_ok=True)
    
    # 同步技能
    used_dir_names = set()
    for entry in entries:
        dest = None
        try:
            dest = resolve_synced_skill_destination_path({
                'targetSkillsDir': target_skills_dir,
                'entry': entry,
                'usedDirNames': used_dir_names
            })
        except Exception as e:
            print(f"Failed to resolve safe destination for {entry.skill['name']}: {str(e)}")
            continue
        
        if not dest:
            print(f"Failed to resolve safe destination for {entry.skill['name']}: invalid source directory name")
            continue
        
        try:
            source_dir_path = entry.skill.get('baseDir')
            if source_dir_path and os.path.exists(source_dir_path):
                shutil.copytree(source_dir_path, dest, dirs_exist_ok=True)
        except Exception as e:
            print(f"Failed to copy {entry.skill['name']} to workspace: {str(e)}")

# ClawHub 集成函数
def search_clawhub_skills(query: str) -> List[Dict]:
    """搜索 ClawHub 技能
    
    Args:
        query: 搜索关键词
        
    Returns:
        搜索结果列表
    """
    return search_skills(query)

def install_clawhub_skill(skill_slug: str, version: Optional[str] = None) -> bool:
    """安装 ClawHub 技能
    
    Args:
        skill_slug: 技能 slug
        version: 技能版本
        
    Returns:
        安装是否成功
    """
    return install_skill(skill_slug, version)

def uninstall_clawhub_skill(skill_slug: str) -> bool:
    """卸载 ClawHub 技能
    
    Args:
        skill_slug: 技能 slug
        
    Returns:
        卸载是否成功
    """
    return uninstall_skill(skill_slug)

def list_clawhub_skills() -> List[Dict]:
    """列出已安装的 ClawHub 技能
    
    Returns:
        已安装技能列表
    """
    return list_skills()

def update_clawhub_skill(skill_slug: Optional[str] = None, version: Optional[str] = None) -> bool:
    """更新 ClawHub 技能
    
    Args:
        skill_slug: 技能 slug
        version: 技能版本
        
    Returns:
        更新是否成功
    """
    return update_skill(skill_slug, version)

# AgentSkills 管理函数
def get_agent_skills() -> List[AgentSkill]:
    """
    获取所有注册的 AgentSkills
    
    Returns:
        AgentSkill 列表
    """
    from .weather_skill import WeatherSkill
    
    return [
        WeatherSkill()
    ]

def find_agent_skill(query: str) -> Optional[AgentSkill]:
    """
    根据查询匹配适合的 AgentSkill
    
    Args:
        query: 用户查询
        
    Returns:
        匹配的 AgentSkill 或 None
    """
    for skill in get_agent_skills():
        if skill.can_handle(query):
            return skill
    return None

def get_agent_skill_metadata() -> List[Dict[str, Any]]:
    """
    获取所有 AgentSkills 的元数据
    
    Returns:
        技能元数据列表
    """
    return [skill.get_metadata() for skill in get_agent_skills()]

