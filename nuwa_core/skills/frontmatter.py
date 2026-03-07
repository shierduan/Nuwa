import re
from typing import Dict, Optional
from .skill_types import OpenClawSkillMetadata, SkillInvocationPolicy

def parse_frontmatter(content: str) -> Dict[str, str]:
    """解析技能卡文件中的frontmatter部分"""
    frontmatter = {}
    # 修改正则表达式，使其能够处理前面的空白字符
    match = re.search(r'^\s*---\n(.*?)\n---', content, re.DOTALL)
    if match:
        frontmatter_content = match.group(1)
        lines = frontmatter_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                # 移除引号
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                frontmatter[key] = value
    return frontmatter

def resolve_open_claw_metadata(frontmatter: Dict[str, str]) -> Optional[OpenClawSkillMetadata]:
    """解析OpenClaw技能元数据"""
    if not frontmatter:
        return None
    
    always = frontmatter.get('always', '').lower() == 'true'
    skill_key = frontmatter.get('skill-key') or frontmatter.get('skill_key')
    primary_env = frontmatter.get('primary-env') or frontmatter.get('primary_env')
    emoji = frontmatter.get('emoji')
    homepage = frontmatter.get('homepage')
    
    # 解析os列表
    os_str = frontmatter.get('os', '')
    os_list = [item.strip() for item in os_str.split(',')] if os_str else []
    
    # 解析requires
    requires = {}
    bins_str = frontmatter.get('requires-bins') or frontmatter.get('requires_bins', '')
    if bins_str:
        requires['bins'] = [item.strip() for item in bins_str.split(',')]
    
    any_bins_str = frontmatter.get('requires-any-bins') or frontmatter.get('requires_any_bins', '')
    if any_bins_str:
        requires['anyBins'] = [item.strip() for item in any_bins_str.split(',')]
    
    env_str = frontmatter.get('requires-env') or frontmatter.get('requires_env', '')
    if env_str:
        requires['env'] = [item.strip() for item in env_str.split(',')]
    
    config_str = frontmatter.get('requires-config') or frontmatter.get('requires_config', '')
    if config_str:
        requires['config'] = [item.strip() for item in config_str.split(',')]
    
    # 解析card元数据
    card = {}
    card_title = frontmatter.get('card-title') or frontmatter.get('card_title')
    if card_title:
        card['title'] = card_title
    
    card_description = frontmatter.get('card-description') or frontmatter.get('card_description')
    if card_description:
        card['description'] = card_description
    
    card_icon = frontmatter.get('card-icon') or frontmatter.get('card_icon')
    if card_icon:
        card['icon'] = card_icon
    
    card_category = frontmatter.get('card-category') or frontmatter.get('card_category')
    if card_category:
        card['category'] = card_category
    
    card_tags_str = frontmatter.get('card-tags') or frontmatter.get('card_tags', '')
    if card_tags_str:
        card['tags'] = [item.strip() for item in card_tags_str.split(',')]
    
    card_color = frontmatter.get('card-color') or frontmatter.get('card_color')
    if card_color:
        card['color'] = card_color
    
    card_background_color = frontmatter.get('card-background-color') or frontmatter.get('card_background_color')
    if card_background_color:
        card['backgroundColor'] = card_background_color
    
    return OpenClawSkillMetadata(
        always=always,
        skill_key=skill_key,
        primary_env=primary_env,
        emoji=emoji,
        homepage=homepage,
        os=os_list,
        requires=requires,
        card=card
    )

def resolve_skill_invocation_policy(frontmatter: Dict[str, str]) -> Optional[SkillInvocationPolicy]:
    """解析技能调用策略"""
    if not frontmatter:
        return None
    
    user_invocable = frontmatter.get('user-invocable', 'true').lower() == 'true'
    disable_model_invocation = frontmatter.get('disable-model-invocation', 'false').lower() == 'true'
    
    return SkillInvocationPolicy(
        user_invocable=user_invocable,
        disable_model_invocation=disable_model_invocation
    )
