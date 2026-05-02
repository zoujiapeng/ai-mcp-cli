import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  FlowGraph, FlowNode, FlowEdge, FlowNodeData,
  ExecutorState, LogEntry, AppSettings, NodeTemplate
} from '@shared/types'

// ── Execution Store ───────────────────────────────────────────────
interface ExecutionStore {
  state: ExecutorState
  activeNodeId: string | null
  logs: LogEntry[]
  dslText: string
  currentTaskId: string | null

  setState: (s: ExecutorState) => void
  setActiveNode: (id: string | null) => void
  addLog: (level: LogEntry['level'], message: string) => void
  clearLogs: () => void
  setDsl: (dsl: string) => void
  setTaskId: (id: string | null) => void
}

export const useExecutionStore = create<ExecutionStore>((set) => ({
  state: 'idle',
  activeNodeId: null,
  logs: [],
  dslText: '',
  currentTaskId: null,

  setState: (state) => set({ state }),
  setActiveNode: (activeNodeId) => set({ activeNodeId }),
  addLog: (level, message) =>
    set((s) => ({
      logs: [
        ...s.logs.slice(-499),
        { id: Date.now().toString(), timestamp: Date.now(), level, message },
      ],
    })),
  clearLogs: () => set({ logs: [] }),
  setDsl: (dslText) => set({ dslText }),
  setTaskId: (currentTaskId) => set({ currentTaskId }),
}))

// ── Flow Graph Store ──────────────────────────────────────────────
interface FlowStore {
  graph: FlowGraph
  selectedNodeId: string | null
  recentFiles: string[]

  setNodes: (nodes: FlowNode[]) => void
  setEdges: (edges: FlowEdge[]) => void
  setGraph: (graph: FlowGraph) => void
  selectNode: (id: string | null) => void
  updateNodeData: (id: string, data: Partial<FlowNodeData>) => void
  addRecentFile: (path: string) => void
  clearGraph: () => void
}

export const useFlowStore = create<FlowStore>()(
  persist(
    (set) => ({
      graph: { nodes: [], edges: [] },
      selectedNodeId: null,
      recentFiles: [],

      setNodes: (nodes) => set((s) => ({ graph: { ...s.graph, nodes } })),
      setEdges: (edges) => set((s) => ({ graph: { ...s.graph, edges } })),
      setGraph: (graph) => set({ graph }),
      selectNode: (selectedNodeId) => set({ selectedNodeId }),
      updateNodeData: (id, data) =>
        set((s) => ({
          graph: {
            ...s.graph,
            nodes: s.graph.nodes.map((n) =>
              n.id === id ? { ...n, data: { ...n.data, ...data } } : n
            ),
          },
        })),
      addRecentFile: (path) =>
        set((s) => ({
          recentFiles: [path, ...s.recentFiles.filter((f) => f !== path)].slice(0, 10),
        })),
      clearGraph: () => set({ graph: { nodes: [], edges: [] } }),
    }),
    { name: 'lobster-flow' }
  )
)

// ── Settings Store ────────────────────────────────────────────────
interface SettingsStore extends AppSettings {
  update: (patch: Partial<AppSettings>) => void
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      apiKey: '',
      backendUrl: 'http://localhost:7788',
      theme: 'dark',
      maxLoops: 9999,
      defaultTimeout: 30,
      retryLimit: 3,
      update: (patch) => set(patch),
    }),
    { name: 'lobster-settings' }
  )
)

// ── Node Template Library ─────────────────────────────────────────
export const NODE_TEMPLATES: NodeTemplate[] = [
  {
    id: 'click',
    type: 'CLICK',
    label: '点击',
    description: '点击指定目标（文字/图像/坐标）',
    icon: '🖱️',
    color: '#3b82f6',
    defaultArgs: '按钮文字',
    category: 'action',
  },
  {
    id: 'wait',
    type: 'WAIT',
    label: '等待',
    description: '等待条件满足',
    icon: '⏳',
    color: '#f59e0b',
    defaultArgs: '加载完成',
    category: 'action',
  },
  {
    id: 'loop',
    type: 'LOOP',
    label: '循环',
    description: '循环执行子节点',
    icon: '🔄',
    color: '#8b5cf6',
    defaultArgs: '主循环',
    category: 'control',
  },
  {
    id: 'condition',
    type: 'CONDITION',
    label: '条件',
    description: 'IF 条件判断',
    icon: '🔀',
    color: '#ec4899',
    defaultArgs: '条件文字',
    category: 'control',
  },
  {
    id: 'macro-fuben',
    type: 'MACRO',
    label: '副本宏',
    description: '执行副本完整流程',
    icon: '⚔️',
    color: '#ef4444',
    defaultArgs: '副本',
    category: 'macro',
  },
  {
    id: 'macro-task',
    type: 'MACRO',
    label: '刷任务宏',
    description: '自动刷任务流程',
    icon: '📋',
    color: '#10b981',
    defaultArgs: '刷任务',
    category: 'macro',
  },
  {
    id: 'macro-reward',
    type: 'MACRO',
    label: '领奖励宏',
    description: '自动领取奖励',
    icon: '🎁',
    color: '#f59e0b',
    defaultArgs: '领取奖励',
    category: 'macro',
  },
  {
    id: 'macro-recover',
    type: 'MACRO',
    label: '自动恢复宏',
    description: '自动恢复状态',
    icon: '💊',
    color: '#06b6d4',
    defaultArgs: '自动恢复',
    category: 'macro',
  },
]
