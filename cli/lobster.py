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
import time
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


def cmd_pause(args):
    """暂停执行"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        resp = requests.post(f"{_backend_url()}/api/executor/pause", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"已暂停 (状态: {data['state']})")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_resume(args):
    """恢复执行"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        resp = requests.post(f"{_backend_url()}/api/executor/resume", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"已恢复 (状态: {data['state']})")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stop(args):
    """停止执行"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        resp = requests.post(f"{_backend_url()}/api/executor/stop", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"已停止 (状态: {data['state']})")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    """查看执行器状态"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        resp = requests.get(f"{_backend_url()}/api/executor/status", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"执行器状态: {data['state']}")
        print(f"队列中: {data['queue']['queued']} 个任务")
        if data['queue']['running']:
            print(f"运行中: {', '.join(data['queue']['running'])}")
        if data['queue']['history']:
            print("最近任务:")
            for h in data['queue']['history'][-5:]:
                print(f"  [{h['status']}] {h['task_id']} ({h['elapsed']}s)")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_macros(args):
    """列出所有可用宏"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        resp = requests.get(f"{_backend_url()}/api/macros", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"可用宏 ({len(data['macros'])}):")
        for m in data['macros']:
            print(f"  - {m}")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_screenshot(args):
    """截图并保存"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        resp = requests.get(f"{_backend_url()}/api/screenshot", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            print(f"截图失败: {data.get('error', '未知错误')}", file=sys.stderr)
            sys.exit(1)
        import base64
        img_data = base64.b64decode(data["image"])
        out_path = args.output or "screenshot.jpg"
        Path(out_path).write_bytes(img_data)
        print(f"截图已保存: {out_path} ({len(img_data) / 1024:.0f} KB)")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_mcp(args):
    """启动 MCP 服务端 (用于 Claude Desktop / Claude Code 集成)"""
    mcp_path = Path(__file__).resolve().parent.parent / "python" / "mcp_server.py"
    if not mcp_path.exists():
        print(f"错误: MCP 服务端不存在 ({mcp_path})", file=sys.stderr)
        sys.exit(1)
    print(f"启动 Lobster MCP 服务端...", file=sys.stderr)
    print(f"后端地址: {_backend_url()}", file=sys.stderr)
    # MCP 使用 stdio 通信, 直接执行 serve 函数
    sys.path.insert(0, str(mcp_path.parent))
    from mcp_server import serve
    serve()


def cmd_logs(args):
    """查看执行器日志"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        resp = requests.get(f"{_backend_url()}/api/logs", params={"count": args.count}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        logs = data.get("logs", [])
        if not logs:
            print("(无日志)")
            return
        for entry in logs[-args.count:]:
            ts = entry.get("ts", 0)
            msg = entry.get("msg", "")
            tstr = time.strftime("%H:%M:%S", time.localtime(ts))
            print(f"[{tstr}] {msg}")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_ocr(args):
    """屏幕 OCR 识别"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        payload = {}
        if args.text:
            payload["target"] = args.text
        resp = requests.post(f"{_backend_url()}/api/perception/ocr", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            print(f"OCR 失败: {data.get('error', '未知错误')}", file=sys.stderr)
            sys.exit(1)
        if args.text:
            if data.get("found"):
                print(f"找到文字: '{data['text']}'")
                print(f"  位置: {data['bbox']}")
                print(f"  中心: {data['center']}")
                print(f"  置信度: {data.get('confidence', '?')}")
            else:
                print(f"未找到文字: '{args.text}'")
        else:
            texts = data.get("texts", [])
            if not texts:
                print("(屏幕未识别到文字)")
                return
            print(f"屏幕识别到 {len(texts)} 个文字区域:")
            for t in texts:
                conf = t.get("confidence", 0)
                label = f"[{t['text']}]"
                print(f"  {label:20s}  center={t['center']}  conf={conf:.2f}")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_find(args):
    """在屏幕上查找图像"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        resp = requests.post(
            f"{_backend_url()}/api/perception/find",
            json={"target": args.image, "threshold": args.threshold},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("found"):
            print(f"找到图像: '{args.image}'")
            print(f"  位置: {data['bbox']}")
            print(f"  中心: {data['center']}")
        else:
            print(f"未找到图像: '{args.image}'")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_env(args):
    """检查运行环境"""
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        resp = requests.get(f"{_backend_url()}/api/env", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"Python: {data['python'].split(chr(10))[0]}")
        print(f"平台: {data['platform']}")
        print(f"模式: {'真实模式' if not data.get('simulation_mode') else '模拟模式'}")
        print(f"截图功能: {'OK' if data.get('screen_capture') else 'FAIL'}")
        print(f"OCR: {'OK' if data.get('ocr_available') else 'FAIL'}")
        print()
        print("依赖状态:")
        for mod, ok in data.get("dependencies", {}).items():
            mark = "OK" if ok else "MISS"
            print(f"  {mod:20s} [{mark}]")
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_restart(args):
    """重启 Python 后端"""
    import subprocess
    import signal

    print("正在重启后端...")
    # 查找并杀掉现有后端进程
    try:
        if sys.platform == "win32":
            subprocess.run("taskkill /f /fi \"WINDOWTITLE eq python*server*\" 2>nul", shell=True)
            subprocess.run("taskkill /f /im python.exe 2>nul | findstr /i server", shell=True)
        else:
            subprocess.run("pkill -f \"python.*server.py\" 2>/dev/null", shell=True)
        time.sleep(1)
    except Exception:
        pass

    # 启动新后端
    backend_dir = Path(__file__).resolve().parent.parent / "python"
    log_path = backend_dir / "server.log"
    port = args.port

    env = os.environ.copy()
    if port:
        env["LOBSTER_PORT"] = str(port)

    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(
                ["python", "server.py"],
                cwd=str(backend_dir),
                env=env,
                stdout=open(log_path, "w", encoding="utf-8"),
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            proc = subprocess.Popen(
                ["python", "server.py"],
                cwd=str(backend_dir),
                env=env,
                stdout=open(log_path, "w", encoding="utf-8"),
                stderr=subprocess.STDOUT,
            )
        print(f"后端已启动 (PID: {proc.pid})")
        print(f"日志: {log_path}")

        # 等待就绪
        url = f"http://localhost:{port or 7788}"
        for i in range(10):
            try:
                r = requests.get(f"{url}/api/health", timeout=2)
                if r.ok:
                    print(f"后端就绪: {url}")
                    return
            except Exception:
                pass
            time.sleep(1)
        print("后端启动中... 可使用 'lobster health' 检查状态")
    except Exception as e:
        print(f"启动失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_run_sync(args):
    """同步执行 DSL (等待完成并查看日志)"""
    dsl = args.dsl
    if dsl == "-" and not sys.stdin.isatty():
        dsl = sys.stdin.read()

    if not dsl or not dsl.strip():
        print("错误: DSL 内容为空", file=sys.stderr)
        sys.exit(1)

    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)

    try:
        print("执行中...")
        resp = requests.post(
            f"{_backend_url()}/api/dsl/run-sync",
            json={
                "dsl": dsl,
                "timeout": args.timeout,
                "max_loops": args.max_loops,
                "retry_limit": args.retry,
            },
            timeout=args.timeout + 10,
        )
        data = resp.json()
        elapsed = data.get("elapsed", 0)

        print(f"\n状态: {data.get('state', '?')}  耗时: {elapsed}s")

        logs = data.get("logs", [])
        if logs:
            print(f"\n执行日志 ({len(logs)} 条):")
            for entry in logs:
                msg = entry.get("msg", "")
                print(f"  {msg}")

        if not data.get("success"):
            print(f"\n错误: {data.get('error', '未知')}", file=sys.stderr)
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_backend_url()})", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.ReadTimeout:
        print("执行超时 (后端仍在运行, 使用 'lobster status' 查看状态)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
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
  lobster run-file task.lobster
  lobster parse "CLICK 目标"
  lobster health
  lobster pause / resume / stop
  lobster status
  lobster macros
  lobster screenshot [path]
  lobster logs [n]            # 查看执行日志
  lobster ocr [文字]          # 屏幕文字识别
  lobster find <图像路径>     # 屏幕图像匹配
  lobster env                 # 检查运行环境
  lobster restart             # 重启后端
  lobster run-sync "CLICK 目标"  # 同步执行并看日志
  lobster api "帮我打开浏览器"
  lobster mcp                 # 启动 MCP 服务端 (Claude Desktop 集成)
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

    # mcp
    p_mcp = subparsers.add_parser("mcp", help="启动 MCP 服务端 (Claude Desktop/Code 集成)")
    p_mcp.add_argument("--port", type=int, help="HTTP 端口 (默认使用 stdio)")

    # pause
    subparsers.add_parser("pause", help="暂停执行")

    # resume
    subparsers.add_parser("resume", help="恢复执行")

    # stop
    subparsers.add_parser("stop", help="停止执行")

    # status
    subparsers.add_parser("status", help="查看执行器状态")

    # macros
    subparsers.add_parser("macros", help="列出可用宏")

    # screenshot
    p_ss = subparsers.add_parser("screenshot", help="截图并保存")
    p_ss.add_argument("output", nargs="?", default="", help="保存路径 (默认: screenshot.jpg)")

    # logs
    p_logs = subparsers.add_parser("logs", help="查看执行器日志")
    p_logs.add_argument("count", nargs="?", type=int, default=50, help="显示条数 (默认: 50)")

    # ocr
    p_ocr = subparsers.add_parser("ocr", help="屏幕 OCR 识别")
    p_ocr.add_argument("text", nargs="?", default="", help="要查找的文字 (留空则提取全部)")

    # find
    p_find = subparsers.add_parser("find", help="在屏幕上查找图像")
    p_find.add_argument("image", help="模板图像路径")
    p_find.add_argument("--threshold", type=float, default=0.7, help="匹配阈值 (默认: 0.7)")

    # env
    subparsers.add_parser("env", help="检查运行环境")

    # restart
    p_restart = subparsers.add_parser("restart", help="重启后端服务")
    p_restart.add_argument("--port", type=int, default=0, help="指定端口")

    # run-sync
    p_rsync = subparsers.add_parser("run-sync", help="同步执行 DSL (等待完成)")
    p_rsync.add_argument("dsl", help="DSL 内容 (或 - 从 stdin)")
    p_rsync.add_argument("--timeout", type=float, default=30.0, help="超时秒数 (默认: 30)")
    p_rsync.add_argument("--max-loops", type=int, default=10, help="最大循环次数 (默认: 10)")
    p_rsync.add_argument("--retry", type=int, default=1, help="失败重试次数 (默认: 1)")

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
        "pause": cmd_pause,
        "resume": cmd_resume,
        "stop": cmd_stop,
        "status": cmd_status,
        "macros": cmd_macros,
        "screenshot": cmd_screenshot,
        "mcp": cmd_mcp,
        "logs": cmd_logs,
        "ocr": cmd_ocr,
        "find": cmd_find,
        "env": cmd_env,
        "restart": cmd_restart,
        "run-sync": cmd_run_sync,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
