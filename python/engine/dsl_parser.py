"""
DSL Parser: 将Lobster DSL文本解析为AST
支持: CLICK, WAIT, LOOP, IF, END, RUN
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional
from enum import Enum


class NodeType(str, Enum):
    CLICK = "CLICK"
    WAIT = "WAIT"
    LOOP = "LOOP"
    IF = "IF"
    END = "END"
    RUN = "RUN"
    SEQUENCE = "SEQUENCE"


@dataclass
class ASTNode:
    type: NodeType
    args: str = ""
    children: List[ASTNode] = field(default_factory=list)
    else_children: List[ASTNode] = field(default_factory=list)
    line: int = 0

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "args": self.args,
            "line": self.line,
            "children": [c.to_dict() for c in self.children],
            "else_children": [c.to_dict() for c in self.else_children],
        }


class DSLParseError(Exception):
    def __init__(self, msg: str, line: int = 0):
        super().__init__(f"[Line {line}] {msg}")
        self.line = line


class DSLParser:
    """
    Lobster DSL 解析器
    语法规则:
      CLICK <target>
      WAIT <condition>
      LOOP [label]
        ...
      END
      IF <condition>
        ...
      [ELSE]
        ...
      END
      RUN <macro_name>
    """

    KEYWORDS = {"CLICK", "WAIT", "LOOP", "IF", "ELSE", "END", "RUN"}

    def __init__(self):
        self._tokens: List[tuple[int, str, str]] = []  # (line, keyword, args)
        self._pos = 0

    def parse(self, source: str) -> ASTNode:
        self._tokens = self._tokenize(source)
        self._pos = 0
        root = ASTNode(type=NodeType.SEQUENCE, args="root")
        root.children = self._parse_block(end_triggers=set())
        return root

    # ── tokenizer ────────────────────────────────────────────────
    def _tokenize(self, source: str) -> List[tuple[int, str, str]]:
        tokens = []
        for lineno, raw in enumerate(source.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^([A-Z]+)\s*(.*)", line)
            if not m:
                raise DSLParseError(f"无法识别的语法: '{line}'", lineno)
            keyword, args = m.group(1), m.group(2).strip()
            if keyword not in self.KEYWORDS:
                raise DSLParseError(f"未知指令: '{keyword}'", lineno)
            tokens.append((lineno, keyword, args))
        return tokens

    # ── recursive descent parser ──────────────────────────────────
    def _peek(self) -> Optional[tuple[int, str, str]]:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _consume(self) -> tuple[int, str, str]:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _parse_block(self, end_triggers: set) -> List[ASTNode]:
        nodes: List[ASTNode] = []
        while self._pos < len(self._tokens):
            tok = self._peek()
            if tok is None:
                break
            lineno, keyword, args = tok
            if keyword in end_triggers or keyword == "END":
                break
            if keyword == "ELSE":
                break
            self._consume()

            if keyword == "CLICK":
                nodes.append(ASTNode(NodeType.CLICK, args, line=lineno))

            elif keyword == "WAIT":
                nodes.append(ASTNode(NodeType.WAIT, args, line=lineno))

            elif keyword == "RUN":
                nodes.append(ASTNode(NodeType.RUN, args, line=lineno))

            elif keyword == "LOOP":
                node = ASTNode(NodeType.LOOP, args, line=lineno)
                node.children = self._parse_block({"END"})
                self._expect("END", lineno)
                nodes.append(node)

            elif keyword == "IF":
                node = ASTNode(NodeType.IF, args, line=lineno)
                node.children = self._parse_block({"END", "ELSE"})
                nxt = self._peek()
                if nxt and nxt[1] == "ELSE":
                    self._consume()
                    node.else_children = self._parse_block({"END"})
                self._expect("END", lineno)
                nodes.append(node)

        return nodes

    def _expect(self, keyword: str, ref_line: int):
        tok = self._peek()
        if tok is None or tok[1] != keyword:
            got = tok[1] if tok else "EOF"
            raise DSLParseError(
                f"期望 '{keyword}'，但得到 '{got}'（从第{ref_line}行的块开始）",
                ref_line,
            )
        self._consume()

    # ── utility ───────────────────────────────────────────────────
    @staticmethod
    def from_string(source: str) -> ASTNode:
        return DSLParser().parse(source)


# ── 快速测试 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    sample = """
# Lobster DSL 示例
CLICK 开始游戏
WAIT 加载完成
LOOP 主循环
  IF 血量低于30%
    RUN 自动恢复
  ELSE
    CLICK 攻击按钮
  END
  RUN 副本
  RUN 领取奖励
  WAIT 结算界面
END
"""
    ast = DSLParser.from_string(sample)
    print(json.dumps(ast.to_dict(), ensure_ascii=False, indent=2))
