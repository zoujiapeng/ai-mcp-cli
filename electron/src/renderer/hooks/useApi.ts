import { useCallback, useEffect, useRef } from 'react'
import axios from 'axios'
import { io, Socket } from 'socket.io-client'
import { useExecutionStore, useSettingsStore } from '../store'

const api = axios.create({ timeout: 10000 })

// ── REST API helpers ──────────────────────────────────────────────
export function useApi() {
  const { backendUrl } = useSettingsStore()

  const parseDsl = useCallback(
    (dsl: string) => api.post(`${backendUrl}/api/dsl/parse`, { dsl }),
    [backendUrl]
  )

  const runDsl = useCallback(
    (dsl: string, options?: { priority?: string; max_loops?: number; timeout?: number }) =>
      api.post(`${backendUrl}/api/dsl/run`, { dsl, ...options }),
    [backendUrl]
  )

  const pauseExecution = useCallback(
    () => api.post(`${backendUrl}/api/executor/pause`),
    [backendUrl]
  )

  const resumeExecution = useCallback(
    () => api.post(`${backendUrl}/api/executor/resume`),
    [backendUrl]
  )

  const stopExecution = useCallback(
    () => api.post(`${backendUrl}/api/executor/stop`),
    [backendUrl]
  )

  const getStatus = useCallback(
    () => api.get(`${backendUrl}/api/executor/status`),
    [backendUrl]
  )

  const generateDsl = useCallback(
    (input: string, apiKey: string) =>
      api.post(`${backendUrl}/api/ai/generate`, { input, api_key: apiKey }),
    [backendUrl]
  )

  const health = useCallback(
    () => api.get(`${backendUrl}/api/health`),
    [backendUrl]
  )

  return { parseDsl, runDsl, pauseExecution, resumeExecution, stopExecution, getStatus, generateDsl, health }
}

// ── WebSocket hook ────────────────────────────────────────────────
export function useSocket() {
  const { backendUrl } = useSettingsStore()
  const { setState, setActiveNode, addLog } = useExecutionStore()
  const socketRef = useRef<Socket | null>(null)

  useEffect(() => {
    const socket = io(backendUrl, {
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    })

    socket.on('connect', () => {
      addLog('success', '✅ 后端连接成功')
    })

    socket.on('disconnect', () => {
      addLog('warn', '⚠️  后端连接断开')
    })

    socket.on('state_change', ({ state }: { state: string }) => {
      setState(state as any)
      addLog('info', `状态变更: ${state}`)
    })

    socket.on('node_start', ({ node_type, args, line }: any) => {
      addLog('info', `▶ [L${line}] ${node_type} ${args}`)
      setActiveNode(`${line}`)
    })

    socket.on('node_done', ({ node_type, args, line }: any) => {
      addLog('success', `✓ [L${line}] ${node_type} ${args}`)
    })

    socket.on('exec_error', ({ message, traceback }: any) => {
      addLog('error', `❌ 错误: ${message}`)
      setState('error')
    })

    socket.on('log', ({ message }: { message: string }) => {
      addLog('info', message)
    })

    socketRef.current = socket

    return () => {
      socket.disconnect()
    }
  }, [backendUrl])

  return socketRef
}

// ── DSL ↔ Flow Graph conversion ───────────────────────────────────
export function dslToGraph(dsl: string): { nodes: any[]; edges: any[] } {
  const lines = dsl.split('\n').filter((l) => l.trim() && !l.trim().startsWith('#'))
  const nodes: any[] = []
  const edges: any[] = []
  let y = 50
  let prevId: string | null = null

  const startNode = {
    id: 'start',
    type: 'lobsterNode',
    position: { x: 300, y: 0 },
    data: { label: '开始', nodeType: 'START', args: '', color: '#22c55e' },
  }
  nodes.push(startNode)
  prevId = 'start'

  lines.forEach((line, idx) => {
    const trimmed = line.trim()
    const m = trimmed.match(/^([A-Z]+)\s*(.*)$/)
    if (!m) return

    const [, cmd, args] = m
    const id = `node-${idx}`
    const colorMap: Record<string, string> = {
      CLICK: '#3b82f6',
      WAIT: '#f59e0b',
      LOOP: '#8b5cf6',
      IF: '#ec4899',
      RUN: '#ef4444',
      END: '#6b7280',
    }

    y += 80
    nodes.push({
      id,
      type: 'lobsterNode',
      position: { x: 300, y },
      data: {
        label: cmd,
        nodeType: cmd,
        args: args.trim(),
        color: colorMap[cmd] || '#6b7280',
      },
    })

    if (prevId) {
      edges.push({
        id: `e-${prevId}-${id}`,
        source: prevId,
        target: id,
        type: 'smoothstep',
        animated: cmd === 'LOOP',
      })
    }
    prevId = id
  })

  return { nodes, edges }
}

export function graphToDsl(nodes: any[], edges: any[]): string {
  const sorted = [...nodes].filter((n) => n.data.nodeType !== 'START' && n.data.nodeType !== 'END')
  sorted.sort((a, b) => a.position.y - b.position.y)

  return sorted
    .map((n) => {
      const { nodeType, args } = n.data
      if (nodeType === 'CONDITION') return `IF ${args}`
      if (nodeType === 'MACRO') return `RUN ${args}`
      return `${nodeType} ${args}`.trim()
    })
    .join('\n')
}
