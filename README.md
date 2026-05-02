# 🦞 Lobster — 低Token AI自动化执行系统

> AI只规划，本地全执行。极简DSL，极低token消耗。
> 用户输入一句话 → AI生成DSL → 本地系统完成所有执行

---

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                   规划层 (LLM)                        │
│  用户输入 → Claude API → DSL输出（1-3次调用）           │
└───────────────────┬─────────────────────────────────┘
                    │ DSL（每行一条指令）
┌───────────────────▼─────────────────────────────────┐
│                   执行层 (Python)                     │
│  DSL解析 → AST → 状态机执行器 → 节点调度               │
│  支持: 循环/条件/子流程/暂停/恢复/停止/自动重试/超时    │
└───────────────────┬─────────────────────────────────┘
                    │ 调用
┌───────────────────▼─────────────────────────────────┐
│                   感知层 (Modules)                    │
│  图像识别(多尺度模板匹配) | OCR(Tesseract) | 交互      │
│  人类行为模拟(贝塞尔曲线) | 弹窗处理 | 进度条检测       │
└─────────────────────────────────────────────────────┘
```

## 项目结构

```
lobster/
├── electron/
│   ├── src/
│   │   ├── main/              # Electron 主进程
│   │   │   ├── main.ts        # 窗口管理 + Python进程管理 + IPC
│   │   │   └── preload.ts     # 安全桥接
│   │   └── renderer/          # React 前端
│   │       ├── components/
│   │       │   ├── Canvas/     # 流程图画布 (React Flow)
│   │       │   ├── NodeLibrary/ # 节点库面板
│   │       │   ├── PropertyPanel/ # 属性编辑面板
│   │       │   └── common/     # TopBar, StatusBar, LogPanel, SettingsModal
│   │       ├── hooks/          # API + WebSocket hooks
│   │       ├── store/          # Zustand 状态管理
│   │       └── styles/         # 全局样式
│   └── public/                 # 静态资源
├── python/
│   ├── server.py               # Flask + SocketIO 后端服务器
│   ├── engine/                 # 核心执行层
│   │   ├── dsl_parser.py       # DSL解析器 → AST
│   │   ├── executor.py         # 状态机执行器 (暂停/恢复/停止/重试)
│   │   └── scheduler.py        # 优先级任务调度器
│   ├── perception/             # 感知层模块
│   │   ├── vision.py           # 截图/模板匹配/变化检测/颜色/进度条/场景
│   │   └── ocr.py              # Tesseract OCR/模糊匹配/文字定位
│   ├── interaction/            # 交互层模块
│   │   └── actions.py          # 人类鼠标/键盘/语义点击/等待/弹窗/宏
│   └── macros/                 # 宏扩展目录
├── cli/
│   └── lobster.py              # 命令行工具
├── shared/
│   └── types.ts                # TypeScript 共享类型
├── lobster.bat                 # Windows CLI入口
├── lobster                     # Unix CLI入口
├── package.json                # 前端依赖
├── tsconfig.json               # TypeScript 配置 (渲染进程)
├── tsconfig.main.json          # TypeScript 配置 (主进程)
├── vite.config.ts              # Vite 构建配置
└── index.html                  # 入口HTML
```

## 快速开始

### 1. 安装前端依赖
```bash
npm install
```

### 2. 安装后端依赖
```bash
cd python
pip install -r requirements.txt

# 如需OCR功能，还需安装Tesseract:
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

### 3. 启动开发模式

```bash
# 终端1: 启动Python后端
cd python && python server.py

# 终端2: 启动Electron + Vite
npm run start
```

或单独启动 Vite 前端开发服务器:
```bash
npm run dev
```

### 4. CLI工具
```bash
# 解析DSL
python cli/lobster.py parse "CLICK 开始游戏"

# 执行DSL（需后端运行）
python cli/lobster.py run "CLICK 开始游戏"

# 从文件读取执行
python cli/lobster.py run-file tasks.lobster

# AI生成DSL（需配置API Key）
ANTHROPIC_API_KEY=sk-ant-... python cli/lobster.py api "帮我打开浏览器搜索天气"

# 检查后端
python cli/lobster.py health
```

## DSL语法

```
CLICK <target>         # 点击目标（文字/图像/坐标 x,y）
WAIT <condition>       # 等待条件: 文字/图像:XXX/稳定/变化/消失:XXX
LOOP <tag>             # 开始循环（标签可选）
IF <condition>         # 条件判断
ELSE                   # 否则分支（可选）
END                    # 结束 LOOP 或 IF 块
RUN <macro>            # 执行宏: 副本/刷任务/领取奖励/自动恢复
```

### 示例
```
CLICK 开始游戏
WAIT 加载完成
LOOP 副本循环
  IF 血量低于30%
    RUN 自动恢复
  ELSE
    CLICK 攻击按钮
  END
  RUN 副本
  RUN 领取奖励
  WAIT 结算界面
END
```

## 三层架构

| 层级 | 技术 | 职责 |
|------|------|------|
| **规划层** | Claude API | 用户输入 → DSL 输出，不参与执行 |
| **执行层** | Python (状态机) | DSL解析→AST→节点调度→暂停/恢复/停止/重试 |
| **感知层** | OpenCV/Tesseract/pyautogui | 图像识别/OCR/鼠标键盘/人类行为模拟 |

## API接口

- `GET /api/health` - 健康检查
- `POST /api/dsl/parse` - DSL解析
- `POST /api/dsl/run` - 提交执行
- `POST /api/executor/pause` - 暂停
- `POST /api/executor/resume` - 恢复
- `POST /api/executor/stop` - 停止
- `GET /api/executor/status` - 状态查询
- `POST /api/ai/generate` - AI生成DSL
- `GET /api/screenshot` - 截图

## 技术栈

- **前端**: Electron 28 + React 18 + TypeScript + Vite 5 + React Flow 11 + Zustand 4
- **后端**: Python 3.10+ / Flask / SocketIO / OpenCV / Tesseract / pyautogui
- **通信**: REST API + WebSocket
