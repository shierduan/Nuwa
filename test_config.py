#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试配置修改功能
"""

import os
import sys
import yaml
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 配置文件路径
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
CONFIG_EXAMPLE = PROJECT_ROOT / "config" / "config_example.yaml"

def read_config():
    """
    读取配置文件
    """
    if not CONFIG_FILE.exists():
        print(f"配置文件不存在: {CONFIG_FILE}")
        return {}
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config or {}
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return {}

def write_config(config):
    """
    写入配置文件
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"写入配置文件失败: {e}")
        return False

def main():
    """
    测试配置修改功能
    """
    print("测试配置修改功能...")
    
    # 检查配置文件是否存在
    if not CONFIG_FILE.exists():
        print(f"配置文件不存在，从示例文件复制: {CONFIG_EXAMPLE}")
        if CONFIG_EXAMPLE.exists():
            import shutil
            shutil.copy2(CONFIG_EXAMPLE, CONFIG_FILE)
            print("配置文件已创建")
        else:
            print(f"示例配置文件不存在: {CONFIG_EXAMPLE}")
            return
    
    # 读取当前配置
    config = read_config()
    print("当前配置:")
    print(f"llm_base_url: {config.get('llm_base_url', '未设置')}")
    
    # 修改配置
    new_url = "https://ark.cn-beijing.volces.com/api/v3"
    config['llm_base_url'] = new_url
    print(f"\n修改 llm_base_url 为: {new_url}")
    
    # 写入配置
    if write_config(config):
        print("配置写入成功")
    else:
        print("配置写入失败")
        return
    
    # 重新读取配置
    config2 = read_config()
    print("\n重新读取的配置:")
    print(f"llm_base_url: {config2.get('llm_base_url', '未设置')}")
    
    # 验证修改是否成功
    if config2.get('llm_base_url') == new_url:
        print("\n✅ 配置修改成功!")
    else:
        print("\n❌ 配置修改失败!")

if __name__ == "__main__":
    main()
