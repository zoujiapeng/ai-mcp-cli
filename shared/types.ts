// ── DSL / AST Types ──────────────────────────────────────────────
export type NodeType = 'CLICK' | 'WAIT' | 'LOOP' | 'IF' | 'RUN' | 'SEQUENCE'

export interface ASTNode {
  type: NodeType
  args: string
  children: ASTNode[]
  else_children: ASTNode[]
  line: number
}

// ── Flow Graph Types ──────────────────────────────────────────────
export interface FlowNodeData {
  label: string
  nodeType: NodeType | 'START' | 'END' | 'CONDITION' | 'LOOP' | 'MACRO'
  args: string
  description?: string
  isActive?: boolean
  hasError?: boolean
  color?: string
}

export interface FlowGraph {
  nodes: FlowNode[]
  edges: FlowEdge[]
}

export interface FlowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: FlowNodeData
}

export interface FlowEdge {
  id: string
  source: string
  target: string
  label?: string
  type?: string
  animated?: boolean
  style?: Record<string, any>
}

// ── Execution Types ───────────────────────────────────────────────
export type ExecutorState = 'idle' | 'running' | 'paused' | 'stopped' | 'error' | 'finished'

export interface ExecutionStatus {
  state: ExecutorState
  currentNode?: string
  currentLine?: number
  loopCounts?: Record<string, number>
}

export interface TaskStatus {
  task_id: string
  status: 'success' | 'error' | 'running' | 'queued'
  elapsed?: number
  error?: string
}

// ── Node Library Types ────────────────────────────────────────────
export interface NodeTemplate {
  id: string
  type: FlowNodeData['nodeType']
  label: string
  description: string
  icon: string
  color: string
  defaultArgs: string
  category: 'action' | 'control' | 'macro' | 'perception'
}

// ── Log ──────────────────────────────────────────────────────────
export interface LogEntry {
  id: string
  timestamp: number
  level: 'info' | 'warn' | 'error' | 'success'
  message: string
}

// ── Settings ─────────────────────────────────────────────────────
export interface AppSettings {
  apiKey: string
  backendUrl: string
  theme: 'dark' | 'light'
  maxLoops: number
  defaultTimeout: number
  retryLimit: number
}
