#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书集成配置检查工具（安全版）

设计原则：
- 凭据只从 config/config.yaml 读取，绝不硬编码到脚本中
- 打印凭据时一律打码，避免密钥泄露到日志/终端

功能：
1. 检查飞书集成所需的 Python 依赖
2. 读取并校验 config/config.yaml 中的 channels.feishu 配置
3. 用真实凭据调用飞书接口验证 appId/appSecret 是否有效
4. 输出清晰的下一步操作指引

用法:
    python feishu_setup_check.py
"""

import os
import sys

try:
    import yaml
except ImportError:
    print("[ERROR] 缺少 pyyaml，请先安装: pip install pyyaml")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[ERROR] 缺少 requests，请先安装: pip install requests")
    sys.exit(1)

CONFIG_PATH = os.path.join("config", "config.yaml")
PLACEHOLDER_PREFIXES = ("YOUR_", "your_", "xxx", "XXX", "TODO", "todo", "")


def mask(secret: str) -> str:
    """对密钥打码，仅保留首尾各 4 位"""
    if not secret:
        return "(空)"
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


def load_config():
    """加载配置文件"""
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] 配置文件不存在: {CONFIG_PATH}")
        print("        请先复制 config/config.local.yaml 为 config/config.yaml 并填入配置")
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[ERROR] 配置文件解析失败: {e}")
        return None


def check_dependencies():
    """检查飞书集成所需的依赖"""
    print("=" * 60)
    print("步骤 1/4：检查依赖")
    print("=" * 60)

    missing = []
    for pkg, import_name in [("lark-oapi", "lark_oapi"), ("websockets", "websockets")]:
        try:
            __import__(import_name)
            print(f"  [OK] {pkg}")
        except ImportError:
            print(f"  [MISSING] {pkg}")
            missing.append(pkg)

    if missing:
        print(f"\n  请先安装缺失依赖:")
        print(f"    pip install {' '.join(missing)}")
        return False
    return True


def check_config_feishu(cfg):
    """检查飞书配置段"""
    print("\n" + "=" * 60)
    print("步骤 2/4：检查飞书配置")
    print("=" * 60)

    channels = cfg.get("channels") or {}
    feishu = channels.get("feishu") or {}

    if not feishu:
        print("  [WARN] 配置中未找到 channels.feishu 段")
        print("         请参考 config/config.local.yaml 补充该配置段")
        return None

    app_id = str(feishu.get("appId", "")).strip()
    app_secret = str(feishu.get("appSecret", "")).strip()
    domain = str(feishu.get("domain", "feishu")).strip()
    enabled = bool(feishu.get("enabled", False))
    bot_name = str(feishu.get("botName", "女娲")).strip()

    print(f"  enabled   : {enabled}")
    print(f"  botName   : {bot_name}")
    print(f"  domain    : {domain}")
    print(f"  appId     : {app_id if app_id else '(空)'}")
    print(f"  appSecret : {mask(app_secret)}")

    is_placeholder = (
        not app_id
        or not app_secret
        or app_id.startswith("YOUR_")
        or app_secret.startswith("YOUR_")
    )

    if is_placeholder:
        print("\n  [WARN] 凭据仍是占位符，无法连接飞书。")
        return {"ok": False, "reason": "placeholder"}
    if not enabled:
        print("\n  [INFO] 飞书渠道未启用 (enabled: false)。")
        return {"ok": False, "reason": "disabled"}

    return {"ok": True, "app_id": app_id, "app_secret": app_secret, "domain": domain}


def verify_credentials(info):
    """调用飞书接口验证凭据"""
    print("\n" + "=" * 60)
    print("步骤 3/4：验证飞书凭据")
    print("=" * 60)

    url = (
        f"https://open.{info['domain']}.cn"
        "/open-apis/auth/v3/app_access_token/internal/"
    )
    print(f"  请求: {url}")

    try:
        resp = requests.post(
            url,
            json={"app_id": info["app_id"], "app_secret": info["app_secret"]},
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        print(f"  HTTP 状态码: {resp.status_code}")

        if resp.status_code != 200:
            print(f"  [FAIL] 请求失败，响应: {resp.text[:300]}")
            return False

        data = resp.json()
        code = data.get("code")
        msg = data.get("msg", "")

        if code == 0:
            token = data.get("app_access_token", "")
            expire = data.get("expire", 0)
            print(f"  [OK] 认证成功！")
            print(f"       token   = {mask(token)}")
            print(f"       有效期  = {expire} 秒")
            return True

        print(f"  [FAIL] 认证失败: code={code}, msg={msg}")
        if code == 10003 or "param" in msg.lower():
            print("         提示: 请检查 appId / appSecret 是否正确、有无多余空格")
        return False

    except Exception as e:
        print(f"  [FAIL] 请求异常: {type(e).__name__}: {e}")
        return False


def print_next_steps(ok):
    """输出下一步指引"""
    print("\n" + "=" * 60)
    print("步骤 4/4：下一步指引")
    print("=" * 60)

    if ok:
        print("""
  凭据有效！接下来请在飞书开放平台完成配置：

  1. 进入 https://open.feishu.cn/app ，选择你的应用
  2. 【权限管理】开通以下权限：
       - im:message            (获取与发送单聊、群组消息)
       - im:message:send_as_bot (以应用身份发送消息)
       - im:chat               (获取群组信息)
  3. 【事件订阅】-> 订阅方式选择「使用长连接接收事件」
     （本项目已采用 WebSocket 长连接，无需公网回调地址）
  4. 添加事件：接收消息 im.message.receive_v1
  5. 创建版本并发布应用，等待管理员审批通过
  6. 重启女娲服务：
       python server_async.py
     日志出现 [OK] 飞书长连接已启动 即表示连接成功
""")
    else:
        print("""
  当前无法连接飞书，请按以下步骤准备凭据：

  1. 打开 https://open.feishu.cn/ ，用你的飞书账号登录
  2. 点击「创建企业自建应用」，填写应用名称（如：女娲）
  3. 在应用「凭证与基础信息」页面获取：
       - App ID     (形如 cli_xxxxxxxxxxxx)
       - App Secret
  4. 将凭据填入 config/config.yaml 的 channels.feishu 段：
       channels:
         feishu:
           appId: "cli_你的真实AppID"
           appSecret: "你的真实AppSecret"
           enabled: true
           botName: "女娲"
  5. 重新运行本脚本验证： python feishu_setup_check.py

  ⚠️ 安全提醒：config/config.yaml 已包含真实密钥，请勿提交到公开仓库。
""")


def main():
    print("=" * 60)
    print("飞书集成配置检查工具")
    print("=" * 60)

    if not check_dependencies():
        sys.exit(1)

    cfg = load_config()
    if cfg is None:
        sys.exit(1)

    info = check_config_feishu(cfg)
    if info is None:
        print_next_steps(False)
        sys.exit(1)

    ok = False
    if info.get("ok"):
        ok = verify_credentials(info)

    print_next_steps(ok)

    print("=" * 60)
    if ok:
        print("✅ 飞书配置检查通过")
    else:
        print("⚠️ 飞书配置尚未就绪，请按指引补充凭据")
    print("=" * 60)

    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
