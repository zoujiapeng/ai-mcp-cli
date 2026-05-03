"""
Lobster MCP 入口 (供 pip entry_point / Claude Desktop 使用)
实际逻辑在 python/mcp_server.py
"""
import sys
import os
from pathlib import Path

# 添加项目根目录和 python 目录到路径
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "python"))
sys.path.insert(0, str(_root))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from mcp_server import main

if __name__ == "__main__":
    main()
