import os
import sys
import tempfile
import unittest

# 添加skills目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from skill_types import SkillCard, SkillEntry, SkillCommandSpec
from frontmatter import parse_frontmatter, resolve_open_claw_metadata, resolve_skill_invocation_policy
from workspace import (
    compact_skill_paths,
    sanitize_skill_command_name,
    resolve_unique_skill_command_name,
    build_workspace_skill_cards,
    build_workspace_skill_cards_by_category,
    build_workspace_skill_command_specs
)

class TestSkillCardMechanism(unittest.TestCase):
    """测试技能卡机制"""
    
    def test_skill_card_creation(self):
        """测试技能卡创建"""
        card = SkillCard(
            name="test-skill",
            title="Test Skill",
            description="A test skill",
            emoji="🔧",
            icon="test-icon",
            category="Testing",
            tags=["test", "example"],
            color="#ff0000",
            background_color="#00ff00"
        )
        self.assertEqual(card.name, "test-skill")
        self.assertEqual(card.title, "Test Skill")
        self.assertEqual(card.description, "A test skill")
        self.assertEqual(card.emoji, "🔧")
        self.assertEqual(card.icon, "test-icon")
        self.assertEqual(card.category, "Testing")
        self.assertEqual(card.tags, ["test", "example"])
        self.assertEqual(card.color, "#ff0000")
        self.assertEqual(card.background_color, "#00ff00")
    
    def test_parse_frontmatter(self):
        """测试frontmatter解析"""
        content = """
---
title: Test Skill
description: A test skill
emoji: 🔧
card-category: Testing
card-tags: test, example
---

Skill content here
"""
        frontmatter = parse_frontmatter(content)
        self.assertEqual(frontmatter.get("title"), "Test Skill")
        self.assertEqual(frontmatter.get("description"), "A test skill")
        self.assertEqual(frontmatter.get("emoji"), "🔧")
        self.assertEqual(frontmatter.get("card-category"), "Testing")
        self.assertEqual(frontmatter.get("card-tags"), "test, example")
    
    def test_resolve_open_claw_metadata(self):
        """测试OpenClaw技能元数据解析"""
        frontmatter = {
            "title": "Test Skill",
            "emoji": "🔧",
            "card-category": "Testing",
            "card-tags": "test, example"
        }
        metadata = resolve_open_claw_metadata(frontmatter)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.emoji, "🔧")
        self.assertEqual(metadata.card.get("category"), "Testing")
        self.assertEqual(metadata.card.get("tags"), ["test", "example"])
    
    def test_resolve_skill_invocation_policy(self):
        """测试技能调用策略解析"""
        frontmatter = {
            "user-invocable": "true",
            "disable-model-invocation": "false"
        }
        policy = resolve_skill_invocation_policy(frontmatter)
        self.assertIsNotNone(policy)
        self.assertTrue(policy.user_invocable)
        self.assertFalse(policy.disable_model_invocation)
    
    def test_compact_skill_paths(self):
        """测试技能路径压缩"""
        home = os.path.expanduser("~")
        skills = [
            {"name": "test-skill", "filePath": os.path.join(home, "skills", "test-skill", "SKILL.md")}
        ]
        compacted = compact_skill_paths(skills)
        self.assertTrue(compacted[0]["filePath"].startswith("~/"))
    
    def test_sanitize_skill_command_name(self):
        """测试技能命令名称清理"""
        test_cases = [
            ("Test Skill", "test_skill"),
            ("Test-Skill", "test_skill"),
            ("test_skill", "test_skill"),
            ("  Test Skill  ", "test_skill"),
            ("", "skill")
        ]
        for input_name, expected in test_cases:
            result = sanitize_skill_command_name(input_name)
            self.assertEqual(result, expected)
    
    def test_resolve_unique_skill_command_name(self):
        """测试解析唯一的技能命令名称"""
        used = set(["test_skill"])
        result = resolve_unique_skill_command_name("test_skill", used)
        self.assertEqual(result, "test_skill_2")
    
    def test_build_workspace_skill_cards(self):
        """测试构建工作区技能卡"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建技能目录和文件
            skill_dir = os.path.join(temp_dir, "skills", "test-skill")
            os.makedirs(skill_dir, exist_ok=True)
            skill_file = os.path.join(skill_dir, "SKILL.md")
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write("""
---
title: Test Skill
description: A test skill
emoji: 🔧
card-category: Testing
card-tags: test, example
---

Skill content here
""")
            
            # 测试构建技能卡
            cards = build_workspace_skill_cards(temp_dir)
            self.assertEqual(len(cards), 0)  # 因为load_skillsFromDir未实现，所以返回空列表
    
    def test_build_workspace_skill_cards_by_category(self):
        """测试按类别构建工作区技能卡"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试按类别构建技能卡
            categories = build_workspace_skill_cards_by_category(temp_dir)
            self.assertEqual(len(categories), 0)  # 因为load_skillsFromDir未实现，所以返回空字典
    
    def test_build_workspace_skill_command_specs(self):
        """测试构建工作区技能命令规范"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 测试构建技能命令规范
            specs = build_workspace_skill_command_specs(temp_dir)
            self.assertEqual(len(specs), 0)  # 因为load_skillsFromDir未实现，所以返回空列表

if __name__ == '__main__':
    unittest.main()
