"""
Lobster MCP (Model Context Protocol) Server
为 Claude Desktop / Claude Code 提供 Lobster 自动化工具

启动方式:
  python mcp_server.py
  lobster mcp

MCP 协议实现: JSON-RPC 2.0 over stdio (Content-Length 头)
"""

from __future__ import annotations
import json
import os
import sys
import time
import uuid
import traceback
from pathlib import Path

# Windows UTF-8 support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

sys.path.insert(0, str(Path(__file__).parent))

BACKEND_URL = os.getenv("LOBSTER_URL", "http://localhost:7788")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ── MCP 协议工具定义 ──────────────────────────────────────────────

TOOLS = [
    {
        "name": "health",
        "description": "检查 Lobster 后端连接状态和执行器状态",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "parse_dsl",
        "description": "解析 DSL 文本为 AST (抽象语法树)，验证语法正确性",
        "inputSchema": {
            "type": "object",
            "properties": {"dsl": {"type": "string", "description": "DSL 源代码"}},
            "required": ["dsl"],
        },
    },
    {
        "name": "run_dsl",
        "description": "提交 DSL 任务到执行器运行",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dsl": {"type": "string", "description": "DSL 源代码"},
                "priority": {"type": "string", "description": "优先级: LOW/NORMAL/HIGH/URGENT", "default": "NORMAL"},
            },
            "required": ["dsl"],
        },
    },
    {
        "name": "pause",
        "description": "暂停正在运行的执行器",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "resume",
        "description": "恢复已暂停的执行器",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "stop",
        "description": "停止正在运行的执行器",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "status",
        "description": "获取执行器详细状态，包括任务队列和运行历史",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "generate_dsl",
        "description": "用自然语言通过 AI 生成 DSL 自动化脚本",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "自然语言描述你要自动化的任务"},
                "api_key": {"type": "string", "description": "Anthropic API Key (可选，默认使用环境变量 ANTHROPIC_API_KEY)"},
            },
            "required": ["input"],
        },
    },
    {
        "name": "list_macros",
        "description": "列出所有可用的内置宏指令",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "screenshot",
        "description": "截取当前屏幕并返回 base64 编码的 JPEG 图像",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_logs",
        "description": "获取执行器最近日志，用于调试执行过程",
        "inputSchema": {
            "type": "object",
            "properties": {"count": {"type": "number", "description": "日志条数 (默认 50)", "default": 50}},
            "required": [],
        },
    },
    {
        "name": "screen_text",
        "description": "对当前屏幕进行 OCR 文字识别，提取所有可见文字",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "可选: 要查找的特定文字，找到返回位置"},
            },
            "required": [],
        },
    },
    {
        "name": "find_on_screen",
        "description": "在屏幕上查找模板图像，返回位置坐标",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "模板图像路径"},
                "threshold": {"type": "number", "description": "匹配阈值 0-1 (默认 0.7)"},
            },
            "required": ["target"],
        },
    },
    {
        "name": "check_env",
        "description": "检查 Python 运行环境、依赖安装状态、感知模块可用性",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "test_action",
        "description": "测试单个动作 (click/wait/ocr/type/macro)，不经过完整 DSL 执行器",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "动作类型: click/wait/ocr/type/macro"},
                "params": {
                    "type": "object",
                    "description": "动作参数，不同动作不同: click={target}, wait={condition}, ocr={target}, type={text}, macro={name}",
                },
            },
            "required": ["action", "params"],
        },
    },
    {
        "name": "run_dsl_sync",
        "description": "同步执行 DSL 脚本，阻塞直到完成，返回完整执行日志和结果",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dsl": {"type": "string", "description": "DSL 源代码"},
                "timeout": {"type": "number", "description": "超时秒数 (默认 30)"},
                "max_loops": {"type": "number", "description": "最大循环次数 (默认 10)"},
            },
            "required": ["dsl"],
        },
    },
]


# ── 工具处理函数 ──────────────────────────────────────────────────

def _call_backend(method: str, path: str, json_data: dict | None = None, timeout: int = 15) -> dict:
    if not HAS_REQUESTS:
        return {"success": False, "error": "缺少 requests 库: pip install requests"}
    url = f"{BACKEND_URL}{path}"
    try:
        if method == "GET":
            resp = requests.get(url, timeout=timeout)
        else:
            resp = requests.post(url, json=json_data or {}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"无法连接后端 ({BACKEND_URL})"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_tool_call(name: str, arguments: dict) -> str:
    if name == "health":
        result = _call_backend("GET", "/api/health")
        if result.get("status") == "ok":
            return (
                f"Lobster 后端运行正常\n"
                f"  状态: {result.get('status')}\n"
                f"  执行器: {result.get('executor_state')}\n"
                f"  模式: {'真实模式' if not result.get('simulation_mode') else '模拟模式'}\n"
                f"  版本: {result.get('version')}"
            )
        return f"后端异常: {result.get('error', '未知')}"

    elif name == "parse_dsl":
        dsl = arguments.get("dsl", "")
        if not dsl.strip():
            return "错误: DSL 内容为空"
        try:
            from engine.dsl_parser import DSLParser
            ast = DSLParser.from_string(dsl)
            return f"解析成功:\n{json.dumps(ast.to_dict(), ensure_ascii=False, indent=2)}"
        except Exception as e:
            return f"解析失败: {e}"

    elif name == "run_dsl":
        dsl = arguments.get("dsl", "")
        priority = arguments.get("priority", "NORMAL")
        result = _call_backend("POST", "/api/dsl/run", {"dsl": dsl, "priority": priority})
        if result.get("success"):
            return f"任务已提交 (ID: {result['task_id']})"
        return f"提交失败: {result.get('error', '未知错误')}"

    elif name == "pause":
        result = _call_backend("POST", "/api/executor/pause")
        return f"执行器已暂停" if result.get("success") else f"操作失败: {result.get('error')}"

    elif name == "resume":
        result = _call_backend("POST", "/api/executor/resume")
        return f"执行器已恢复" if result.get("success") else f"操作失败: {result.get('error')}"

    elif name == "stop":
        result = _call_backend("POST", "/api/executor/stop")
        return f"执行器已停止" if result.get("success") else f"操作失败: {result.get('error')}"

    elif name == "status":
        result = _call_backend("GET", "/api/executor/status")
        if "state" not in result:
            return f"获取状态失败: {result.get('error', '未知')}"
        lines = [f"执行器状态: {result['state']}"]
        queue = result.get("queue", {})
        lines.append(f"队列中: {queue.get('queued', 0)} 个任务")
        running = queue.get("running", [])
        if running:
            lines.append(f"运行中: {', '.join(running)}")
        history = queue.get("history", [])
        if history:
            lines.append("最近任务:")
            for h in history[-5:]:
                lines.append(f"  [{h['status']}] {h['task_id']} ({h['elapsed']}s)")
        return "\n".join(lines)

    elif name == "generate_dsl":
        user_input = arguments.get("input", "")
        api_key = arguments.get("api_key") or os.getenv("ANTHROPIC_API_KEY", "")
        result = _call_backend("POST", "/api/ai/generate", {"input": user_input, "api_key": api_key}, timeout=30)
        if result.get("success"):
            dsl = result["dsl"]
            usage = result.get("usage", {})
            return (
                f"生成的 DSL:\n```\n{dsl}\n```\n"
                f"(Tokens: 输入={usage.get('input_tokens', '?')} 输出={usage.get('output_tokens', '?')})"
            )
        return f"生成失败: {result.get('error', '未知错误')}"

    elif name == "list_macros":
        result = _call_backend("GET", "/api/macros")
        macros = result.get("macros", [])
        if macros:
            return f"可用宏 ({len(macros)}):\n" + "\n".join(f"  - {m}" for m in macros)
        return "没有可用宏"

    elif name == "screenshot":
        result = _call_backend("GET", "/api/screenshot", timeout=15)
        if result.get("success"):
            return f"data:image/jpeg;base64,{result['image']}"
        return f"截图失败: {result.get('error', '未知错误')}"

    elif name == "get_logs":
        count = arguments.get("count", 50)
        result = _call_backend("GET", f"/api/logs?count={count}")
        logs = result.get("logs", [])
        if not logs:
            return "(无日志)"
        lines = [f"执行日志 (最近 {len(logs)} 条):"]
        for entry in logs:
            ts = entry.get("ts", 0)
            msg = entry.get("msg", "")
            tstr = time.strftime("%H:%M:%S", time.localtime(ts))
            lines.append(f"[{tstr}] {msg}")
        return "\n".join(lines)

    elif name == "screen_text":
        target = arguments.get("target", "")
        payload = {}
        if target:
            payload["target"] = target
        result = _call_backend("POST", "/api/perception/ocr", payload, timeout=15)
        if not result.get("success"):
            return f"OCR 失败: {result.get('error', '未知')}"
        if target:
            if result.get("found"):
                return (
                    f"找到文字: '{result['text']}'\n"
                    f"  位置: {result['bbox']}\n"
                    f"  中心: {result['center']}\n"
                    f"  置信度: {result.get('confidence', '?')}"
                )
            return f"未找到文字: '{target}'"
        else:
            texts = result.get("texts", [])
            if not texts:
                return "(屏幕未识别到文字)"
            lines = [f"屏幕识别到 {len(texts)} 个文字区域:"]
            for t in texts:
                conf = t.get("confidence", 0)
                lines.append(f"  [{t['text']}] center={t['center']} conf={conf:.2f}")
            return "\n".join(lines)

    elif name == "find_on_screen":
        target = arguments.get("target", "")
        threshold = arguments.get("threshold", 0.7)
        result = _call_backend(
            "POST", "/api/perception/find",
            {"target": target, "threshold": threshold},
            timeout=15,
        )
        if result.get("found"):
            return f"找到图像: '{target}'\n  位置: {result['bbox']}\n  中心: {result['center']}"
        return f"未找到图像: '{target}'"

    elif name == "check_env":
        result = _call_backend("GET", "/api/env")
        lines = [
            f"Python: {result.get('python', '?').split(chr(10))[0]}",
            f"平台: {result.get('platform', '?')}",
            f"模式: {'真实模式' if not result.get('simulation_mode') else '模拟模式'}",
            f"截图: {'OK' if result.get('screen_capture') else 'FAIL'}",
            f"OCR: {'OK' if result.get('ocr_available') else 'FAIL'}",
            "",
            "依赖:",
        ]
        for mod, ok in result.get("dependencies", {}).items():
            lines.append(f"  {mod}: {'OK' if ok else 'MISS'}")
        return "\n".join(lines)

    elif name == "test_action":
        action = arguments.get("action", "")
        params = arguments.get("params", {})
        result = _call_backend(
            "POST", "/api/action/test",
            {"action": action, "params": params},
            timeout=30,
        )
        if result.get("success"):
            if result.get("simulated"):
                return f"[模拟] 动作 '{action}' 执行成功 (params={params})"
            return f"动作 '{action}' 执行成功: {json.dumps(result, ensure_ascii=False)}"
        return f"动作执行失败: {result.get('error', '未知')}"

    elif name == "run_dsl_sync":
        dsl = arguments.get("dsl", "")
        if not dsl.strip():
            return "错误: DSL 内容为空"
        payload = {
            "dsl": dsl,
            "timeout": arguments.get("timeout", 30),
            "max_loops": arguments.get("max_loops", 10),
            "retry_limit": 1,
        }
        timeout = payload["timeout"] + 10
        result = _call_backend("POST", "/api/dsl/run-sync", payload, timeout=timeout)
        elapsed = result.get("elapsed", 0)
        lines = [f"状态: {result.get('state', '?')}  耗时: {elapsed}s"]
        logs = result.get("logs", [])
        if logs:
            lines.append(f"\n执行日志 ({len(logs)} 条):")
            for entry in logs:
                lines.append(f"  {entry.get('msg', '')}")
        if not result.get("success"):
            lines.append(f"\n错误: {result.get('error', '未知')}")
        return "\n".join(lines)

    return f"未知工具: {name}"


# ── MCP stdio 协议传输 ──────────────────────────────────────────

def _read_message() -> dict | None:
    """从 stdin 读取 MCP 消息 (Content-Length 头 + JSON)"""
    content_length = 0
    while True:
        line = sys.stdin.readline()
        if not line:
            return None  # EOF
        line = line.strip()
        if not line:
            break
        if line.lower().startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass

    if content_length <= 0:
        return None

    raw = sys.stdin.read(content_length)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _send_message(msg: dict):
    """发送 MCP 消息到 stdout (Content-Length 头 + JSON)"""
    payload = json.dumps(msg, ensure_ascii=False)
    data = f"Content-Length: {len(payload.encode('utf-8'))}\r\n\r\n{payload}"
    sys.stdout.write(data)
    sys.stdout.flush()


def serve():
    """主循环: 读取 MCP 请求并处理"""
    initialized = False

    while True:
        msg = _read_message()
        if msg is None:
            break

        method = msg.get("method", "")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        # 通知类消息 (无 id)
        if msg_id is None:
            if method == "notifications/initialized":
                initialized = True
            continue

        # ── initialize ──
        if method == "initialize":
            _send_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "lobster-mcp", "version": "1.0.0"},
                },
            })
            initialized = True

        # ── tools/list ──
        elif method == "tools/list":
            _send_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOLS},
            })

        # ── tools/call ──
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                text = handle_tool_call(tool_name, arguments)
                _send_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": text}],
                    },
                })
            except Exception as e:
                _send_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": f"工具执行失败: {e}"},
                })

        # ── 其他方法 (ping, 等) ──
        elif method == "ping":
            _send_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {},
            })

        else:
            _send_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {},
            })


def main():
    """独立入口"""
    serve()


if __name__ == "__main__":
    main()
