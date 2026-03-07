from typing import Dict, List, Optional, Union

class SkillInstallSpec:
    def __init__(self,
                 id: Optional[str] = None,
                 kind: str = "",
                 label: Optional[str] = None,
                 bins: Optional[List[str]] = None,
                 os: Optional[List[str]] = None,
                 formula: Optional[str] = None,
                 package: Optional[str] = None,
                 module: Optional[str] = None,
                 url: Optional[str] = None,
                 archive: Optional[str] = None,
                 extract: bool = False,
                 strip_components: Optional[int] = None,
                 target_dir: Optional[str] = None):
        self.id = id
        self.kind = kind
        self.label = label
        self.bins = bins or []
        self.os = os or []
        self.formula = formula
        self.package = package
        self.module = module
        self.url = url
        self.archive = archive
        self.extract = extract
        self.strip_components = strip_components
        self.target_dir = target_dir

class OpenClawSkillMetadata:
    def __init__(self,
                 always: Optional[bool] = None,
                 skill_key: Optional[str] = None,
                 primary_env: Optional[str] = None,
                 emoji: Optional[str] = None,
                 homepage: Optional[str] = None,
                 os: Optional[List[str]] = None,
                 requires: Optional[Dict[str, List[str]]] = None,
                 install: Optional[List[SkillInstallSpec]] = None,
                 card: Optional[Dict[str, Union[str, List[str]]]] = None):
        self.always = always
        self.skill_key = skill_key
        self.primary_env = primary_env
        self.emoji = emoji
        self.homepage = homepage
        self.os = os or []
        self.requires = requires or {}
        self.install = install or []
        self.card = card or {}

class SkillInvocationPolicy:
    def __init__(self,
                 user_invocable: bool = True,
                 disable_model_invocation: bool = False):
        self.user_invocable = user_invocable
        self.disable_model_invocation = disable_model_invocation

class SkillCommandDispatchSpec:
    def __init__(self,
                 kind: str = "tool",
                 tool_name: str = "",
                 arg_mode: Optional[str] = None):
        self.kind = kind
        self.tool_name = tool_name
        self.arg_mode = arg_mode

class SkillCommandSpec:
    def __init__(self,
                 name: str = "",
                 skill_name: str = "",
                 description: str = "",
                 dispatch: Optional[SkillCommandDispatchSpec] = None,
                 card: Optional[Dict[str, Union[str, List[str]]]] = None):
        self.name = name
        self.skill_name = skill_name
        self.description = description
        self.dispatch = dispatch
        self.card = card

class SkillsInstallPreferences:
    def __init__(self,
                 prefer_brew: bool = True,
                 node_manager: str = "npm"):
        self.prefer_brew = prefer_brew
        self.node_manager = node_manager

class SkillCard:
    def __init__(self,
                 name: str = "",
                 title: Optional[str] = None,
                 description: Optional[str] = None,
                 emoji: Optional[str] = None,
                 icon: Optional[str] = None,
                 category: Optional[str] = None,
                 tags: Optional[List[str]] = None,
                 color: Optional[str] = None,
                 background_color: Optional[str] = None):
        self.name = name
        self.title = title
        self.description = description
        self.emoji = emoji
        self.icon = icon
        self.category = category
        self.tags = tags or []
        self.color = color
        self.background_color = background_color

class SkillEntry:
    def __init__(self,
                 skill: Dict,
                 frontmatter: Dict[str, str],
                 metadata: Optional[OpenClawSkillMetadata] = None,
                 invocation: Optional[SkillInvocationPolicy] = None,
                 card: Optional[SkillCard] = None):
        self.skill = skill
        self.frontmatter = frontmatter
        self.metadata = metadata
        self.invocation = invocation
        self.card = card

class SkillEligibilityContext:
    def __init__(self,
                 remote: Optional[Dict] = None):
        self.remote = remote

class SkillSnapshot:
    def __init__(self,
                 prompt: str = "",
                 skills: List[Dict] = None,
                 skill_filter: Optional[List[str]] = None,
                 resolved_skills: Optional[List[Dict]] = None,
                 version: Optional[int] = None):
        self.prompt = prompt
        self.skills = skills or []
        self.skill_filter = skill_filter
        self.resolved_skills = resolved_skills
        self.version = version
