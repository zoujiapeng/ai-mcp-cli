"""
Lobster Python 后端服务器
提供 REST API + WebSocket 实时通信
供 Electron 前端调用
"""

from __future__ import annotations
import json
import os
import sys
import time
import threading
import uuid
from pathlib import Path
from typing import Any

# Windows UTF-8 support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from engine.dsl_parser import DSLParser
from engine.executor import DSLExecutor, ExecutorState, ExecutionContext
from engine.scheduler import TaskScheduler, TaskPriority

# 尝试导入动作处理器（可选，若依赖库未安装则用模拟模式）
try:
    from interaction.actions import ActionHandler
    action_handler = ActionHandler()
    SIMULATION_MODE = False
    print("[OK] 动作处理器加载成功 (真实模式)")
except ImportError as e:
    action_handler = None
    SIMULATION_MODE = True
    print(f"[WARN] 动作处理器加载失败，进入模拟模式: {e}")

# ── 初始化 ──────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = "lobster-secret"
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

executor = DSLExecutor(action_handler=action_handler)
scheduler = TaskScheduler(executor)

# 日志缓存 (供调试用)
_executor_logs: list[dict] = []
_MAX_LOGS = 1000


def broadcast_event(event: str, data: dict):
    """向所有连接的客户端广播事件"""
    socketio.emit(event, data)


# 注册执行器事件
executor.on("node_start", lambda **kw: broadcast_event("node_start", kw))
executor.on("node_done", lambda **kw: broadcast_event("node_done", kw))
executor.on("error", lambda **kw: broadcast_event("exec_error", kw))
executor.on("state_change", lambda **kw: broadcast_event("state_change", kw))
executor.on("log", lambda **kw: (_executor_logs.append({"ts": time.time(), "msg": kw.get("message", "")}) or len(_executor_logs) > _MAX_LOGS and _executor_logs.pop(0)) or broadcast_event("log", kw))

scheduler.start()


# ── REST API ──────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "simulation_mode": SIMULATION_MODE,
        "executor_state": executor.state.value,
        "version": "1.0.0",
    })


@app.route("/api/dsl/parse", methods=["POST"])
def parse_dsl():
    """解析 DSL → AST（不执行）"""
    data = request.get_json()
    source = data.get("dsl", "")
    try:
        ast = DSLParser.from_string(source)
        return jsonify({"success": True, "ast": ast.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/dsl/run", methods=["POST"])
def run_dsl():
    """提交 DSL 执行任务"""
    data = request.get_json()
    source = data.get("dsl", "")
    priority = data.get("priority", "NORMAL")
    task_id = data.get("task_id") or str(uuid.uuid4())

    ctx = ExecutionContext(
        max_loops=data.get("max_loops", 9999),
        retry_limit=data.get("retry_limit", 3),
        timeout=data.get("timeout", 30.0),
    )

    try:
        # 先验证 DSL 语法
        DSLParser.from_string(source)

        prio = getattr(TaskPriority, priority, TaskPriority.NORMAL)
        scheduler.submit(task_id, source, priority=prio)
        return jsonify({"success": True, "task_id": task_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/executor/pause", methods=["POST"])
def pause_executor():
    executor.pause()
    return jsonify({"success": True, "state": executor.state.value})


@app.route("/api/executor/resume", methods=["POST"])
def resume_executor():
    executor.resume()
    return jsonify({"success": True, "state": executor.state.value})


@app.route("/api/executor/stop", methods=["POST"])
def stop_executor():
    executor.stop()
    return jsonify({"success": True, "state": executor.state.value})


@app.route("/api/executor/status", methods=["GET"])
def executor_status():
    return jsonify({
        "state": executor.state.value,
        "queue": scheduler.get_queue_status(),
    })


@app.route("/api/ai/generate", methods=["POST"])
def generate_dsl():
    """调用 Claude API 生成 DSL"""
    data = request.get_json()
    user_input = data.get("input", "")
    api_key = data.get("api_key") or os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        return jsonify({"success": False, "error": "未提供 ANTHROPIC_API_KEY"}), 400

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = """你是 Lobster 自动化系统的规划引擎。
用户提出任务需求，你必须用以下 DSL 语法生成执行计划：

指令集（每行一条）:
  CLICK <目标>      # 点击文字、图像或坐标
  WAIT <条件>       # 等待条件: 文字/图像/稳定/变化/消失:XXX
  LOOP <标签>       # 开始循环
  IF <条件>         # 条件判断（条件同 WAIT）
  ELSE              # 否则分支（可选）
  END               # 结束 LOOP 或 IF 块
  RUN <宏名称>      # 执行内置宏: 副本/刷任务/领取奖励/自动恢复

规则：
- 只输出 DSL 代码，不加任何解释
- 以 # 开头的行为注释
- 目标尽量使用用户界面中可见的文字

示例:
用户: "开始游戏，进入副本刷10次，结束后领奖励"
输出:
CLICK 开始游戏
WAIT 主界面
LOOP 副本循环
  RUN 副本
  RUN 领取奖励
  WAIT 结算界面
END"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_input}],
        )

        dsl_text = message.content[0].text.strip()

        # 验证 DSL 可解析
        try:
            ast = DSLParser.from_string(dsl_text)
            ast_dict = ast.to_dict()
        except Exception as parse_err:
            ast_dict = None

        return jsonify({
            "success": True,
            "dsl": dsl_text,
            "ast": ast_dict,
            "usage": {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            },
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/macros", methods=["GET"])
def list_macros():
    """列出所有可用宏"""
    builtin = ["副本", "刷任务", "领取奖励", "自动恢复"]
    return jsonify({"macros": builtin})


@app.route("/api/screenshot", methods=["GET"])
def take_screenshot():
    """截图并返回 base64"""
    try:
        from perception.vision import ScreenCapture
        import base64, cv2
        img = ScreenCapture.capture()
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 60])
        b64 = base64.b64encode(buf).decode()
        return jsonify({"success": True, "image": b64, "format": "jpeg"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/logs", methods=["GET"])
def get_logs():
    """获取执行器日志"""
    count = request.args.get("count", 50, type=int)
    return jsonify({"logs": _executor_logs[-count:]})


@app.route("/api/perception/ocr", methods=["POST"])
def ocr_screen():
    """对屏幕或指定区域进行 OCR 文字识别"""
    data = request.get_json() or {}
    region = data.get("region")  # [x,y,w,h]
    target = data.get("target")  # 可选: 查找特定文字
    try:
        from perception.ocr import OCREngine
        ocr = OCREngine()
        if target:
            result = ocr.find_text(target, region=region)
            if result:
                return jsonify({
                    "success": True,
                    "found": True,
                    "text": result.text,
                    "bbox": result.bbox,
                    "center": result.center,
                    "confidence": result.confidence,
                })
            return jsonify({"success": True, "found": False, "text": None})
        else:
            results = ocr.extract_all(region=region)
            return jsonify({
                "success": True,
                "texts": [
                    {"text": r.text, "bbox": r.bbox, "center": r.center, "confidence": r.confidence}
                    for r in results
                ],
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/perception/find", methods=["POST"])
def find_image():
    """在屏幕上查找模板图像"""
    data = request.get_json() or {}
    target = data.get("target", "")
    region = data.get("region")
    threshold = data.get("threshold", 0.7)
    try:
        from perception.vision import TemplateMatcher
        matcher = TemplateMatcher()
        result = matcher.find(target, region=region, threshold=threshold)
        if result:
            return jsonify({
                "success": True,
                "found": True,
                "bbox": result,
                "center": [(result[0] + result[2]) // 2, (result[1] + result[3]) // 2],
            })
        return jsonify({"success": True, "found": False})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/env", methods=["GET"])
def check_env():
    """检查 Python 运行环境"""
    info = {
        "python": sys.version,
        "platform": sys.platform,
        "simulation_mode": SIMULATION_MODE,
        "backend_url": f"http://localhost:{os.getenv('LOBSTER_PORT', '7788')}",
    }
    # 检查关键依赖
    deps = {}
    for mod_name, import_name in [
        ("requests", "requests"),
        ("opencv", "cv2"),
        ("numpy", "numpy"),
        ("Pillow", "PIL"),
        ("pyautogui", "pyautogui"),
        ("mss", "mss"),
        ("pytesseract", "pytesseract"),
        ("flask", "flask"),
        ("flask-cors", "flask_cors"),
        ("flask-socketio", "flask_socketio"),
        ("anthropic", "anthropic"),
    ]:
        try:
            __import__(import_name)
            deps[mod_name] = True
        except ImportError:
            deps[mod_name] = False
    info["dependencies"] = deps

    # 感知模块状态
    try:
        from perception.vision import ScreenCapture
        ScreenCapture.capture()
        info["screen_capture"] = True
    except Exception:
        info["screen_capture"] = False

    try:
        from perception.ocr import OCREngine
        ocr = OCREngine()
        ocr.extract_all()
        info["ocr_available"] = True
    except Exception:
        info["ocr_available"] = False

    return jsonify(info)


@app.route("/api/action/test", methods=["POST"])
def test_action():
    """测试单个动作 (不经过 DSL 执行器)"""
    data = request.get_json() or {}
    action = data.get("action", "click")
    params = data.get("params", {})

    if SIMULATION_MODE or action_handler is None:
        return jsonify({"success": True, "simulated": True, "action": action, "params": params})

    try:
        if action == "click":
            target = params.get("target", "")
            result = action_handler.clicker.click(target, timeout=params.get("timeout", 10))
            return jsonify({"success": True, "clicked": result})
        elif action == "wait":
            condition = params.get("condition", "")
            result = action_handler.waiter.wait(condition, timeout=params.get("timeout", 30))
            return jsonify({"success": True, "condition_met": result})
        elif action == "ocr":
            target = params.get("target", "")
            result = action_handler.ocr.find_text(target)
            if result:
                return jsonify({"success": True, "found": True, "text": result.text, "center": result.center})
            return jsonify({"success": True, "found": False})
        elif action == "type":
            text = params.get("text", "")
            from interaction.actions import HumanKeyboard
            HumanKeyboard.type_text(text)
            return jsonify({"success": True, "typed": True})
        elif action == "macro":
            name = params.get("name", "")
            result = action_handler._handle_macro(name, ctx=None)
            return jsonify({"success": True, "macro_executed": result})
        else:
            return jsonify({"success": False, "error": f"未知动作: {action}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dsl/run-sync", methods=["POST"])
def run_dsl_sync():
    """同步执行 DSL (阻塞直到完成, 返回日志和结果)"""
    data = request.get_json()
    source = data.get("dsl", "")

    if not source.strip():
        return jsonify({"success": False, "error": "DSL 内容为空"}), 400

    start = time.time()
    logs_before = len(_executor_logs)

    try:
        # 验证语法
        DSLParser.from_string(source)

        ctx = ExecutionContext(
            max_loops=data.get("max_loops", 10),
            retry_limit=data.get("retry_limit", 1),
            timeout=data.get("timeout", 30.0),
        )

        # 同步执行
        executor.run_dsl_sync(source, ctx=ctx)
        elapsed = time.time() - start

        logs = _executor_logs[logs_before:]
        return jsonify({
            "success": True,
            "state": executor.state.value,
            "elapsed": round(elapsed, 2),
            "logs": [{"ts": l["ts"], "msg": l["msg"]} for l in logs],
        })
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        logs = _executor_logs[logs_before:]
        return jsonify({
            "success": False,
            "error": str(e),
            "elapsed": elapsed,
            "logs": [{"ts": l["ts"], "msg": l["msg"]} for l in logs],
        }), 400


# ── WebSocket 事件 ────────────────────────────────────────────────
@socketio.on("connect")
def on_connect():
    emit("connected", {"msg": "Lobster 后端连接成功", "simulation_mode": SIMULATION_MODE})


@socketio.on("ping")
def on_ping():
    emit("pong", {"ts": time.time()})


@socketio.on("run_dsl")
def on_run_dsl(data):
    source = data.get("dsl", "")
    task_id = str(uuid.uuid4())
    try:
        DSLParser.from_string(source)
        scheduler.submit(task_id, source)
        emit("task_submitted", {"task_id": task_id})
    except Exception as e:
        emit("exec_error", {"error": str(e)})


# ── 启动 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("LOBSTER_PORT", "7788"))
    print(f"""
{"="*44}
   Lobster Backend v1.0.0
  Port: {port:<5}  Mode: {"SIMULATE" if SIMULATION_MODE else "REAL    "}
{"="*44}
""")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
