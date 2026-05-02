#!/usr/bin/env python3
"""
Lobster CLI - 命令行自动化工具

用法:
  lobster run "CLICK 开始游戏\\nWAIT 加载完成"
  lobster run-file task.lobster
  lobster parse "CLICK 目标"
  lobster health
  lobster api "帮我打开浏览器并搜索天气"
"""

import sys
import os
import json
import argparse
import re
from pathlib import Path

# Windows UTF-8 support
if sys.platform == "win32":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 添加 python 目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


BACKEND_URL = os.getenv("LOBSTER_URL", "http://localhost:7788")
BACKEND_TIMEOUT = 15

def _backend_url():
    return os.environ.get("LOBSTER_URL", BACKEND_URL)


def cmd_run(args):
    """执行 DSL"""
    dsl = args.dsl
    if dsl == "-" and not sys.stdin.isatty():
        dsl = sys.stdin.read()

    if not dsl or not dsl.strip():
        print("❌ 错误: DSL 内容为空", file=sys.stderr)
        sys.exit(1)

    if not HAS_REQUESTS:
        print("📝 DSL 内容:")
        print(dsl)
        print("\n⚠️  需要安装 requests 库才能提交到后端: pip install requests")
        return

    try:
        resp = requests.post(
            f"{_backend_url()}/api/dsl/run",
            json={"dsl": dsl, "priority": "NORMAL"},
            timeout=BACKEND_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            print(f"✅ 任务已提交, ID: {data['task_id']}")
            print(f"   查看状态: {_backend_url()}/api/executor/status")
        else:
            print(f"❌ 提交失败: {data.get('error', '未知错误')}", file=sys.stderr)
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接后端 ({_backend_url()})", file=sys.stderr)
        print("   请确保 Python 后端已启动:", file=sys.stderr)
        print(f"   cd python && python server.py", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_run_file(args):
    """从文件读取 DSL 并执行"""
    path = Path(args.file)
    if not path.exists():
        print(f"❌ 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    dsl = path.read_text("utf-8")
    args.dsl = dsl
    cmd_run(args)


def cmd_parse(args):
    """解析 DSL 并输出 AST"""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
    try:
        from engine.dsl_parser import DSLParser
        ast = DSLParser.from_string(args.dsl)
        print(json.dumps(ast.to_dict(), ensure_ascii=False, indent=2))
    except ImportError as e:
        print(f"❌ 无法导入解析器: {e}", file=sys.stderr)
        print("   请确保在项目根目录运行", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 解析失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_health(args):
    """检查后端健康状态"""
    if not HAS_REQUESTS:
        print("⚠️  需要安装 requests 库: pip install requests")
        return

    try:
        resp = requests.get(f"{_backend_url()}/api/health", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ 后端状态: {data.get('status', 'unknown')}")
        print(f"   执行器状态: {data.get('executor_state', 'unknown')}")
        print(f"   模拟模式: {data.get('simulation_mode', True)}")
        print(f"   版本: {data.get('version', '?')}")
    except requests.exceptions.ConnectionError:
        print(f"❌ 后端未运行 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 检查失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_api(args):
    """调用 AI 生成 DSL"""
    api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ 需要设置 ANTHROPIC_API_KEY", file=sys.stderr)
        print("   方式1: export ANTHROPIC_API_KEY=sk-ant-...", file=sys.stderr)
        print("   方式2: lobster --api-key sk-ant-... api '你的需求'", file=sys.stderr)
        sys.exit(1)

    if not HAS_REQUESTS:
        print("❌ 需要安装 requests 库", file=sys.stderr)
        sys.exit(1)

    try:
        resp = requests.post(
            f"{_backend_url()}/api/ai/generate",
            json={"input": args.text, "api_key": api_key},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            print(data["dsl"])
            usage = data.get("usage", {})
            print(f"\n# Tokens: 输入={usage.get('input_tokens', '?')} 输出={usage.get('output_tokens', '?')}")
        else:
            print(f"❌ 生成失败: {data.get('error', '未知错误')}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"❌ 请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="🦞 Lobster - 低Token AI自动化执行系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  lobster run "CLICK 开始游戏"
  lobster run "CLICK 开始游戏\\nWAIT 加载完成" | head
  lobster run-file task.lobster
  lobster parse "CLICK 目标"
  lobster health
  lobster api "帮我打开浏览器"
        """,
    )
    parser.add_argument("--url", default=BACKEND_URL, help="后端 URL (默认: http://localhost:7788)")
    parser.add_argument("--api-key", help="Anthropic API Key")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run
    p_run = subparsers.add_parser("run", help="执行 DSL")
    p_run.add_argument("dsl", help="DSL 内容（使用 \\n 换行，或 - 从 stdin 读取）")

    # run-file
    p_runf = subparsers.add_parser("run-file", help="从文件执行 DSL")
    p_runf.add_argument("file", help=".lobster 文件路径")

    # parse
    p_parse = subparsers.add_parser("parse", help="解析 DSL 为 AST")
    p_parse.add_argument("dsl", help="DSL 内容")

    # health
    subparsers.add_parser("health", help="检查后端状态")

    # api
    p_api = subparsers.add_parser("api", help="AI 生成 DSL")
    p_api.add_argument("text", help="自然语言描述任务")

    args = parser.parse_args()

    if args.url and args.url != BACKEND_URL:
        os.environ["LOBSTER_URL"] = args.url

    commands = {
        "run": cmd_run,
        "run-file": cmd_run_file,
        "parse": cmd_parse,
        "health": cmd_health,
        "api": cmd_api,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
