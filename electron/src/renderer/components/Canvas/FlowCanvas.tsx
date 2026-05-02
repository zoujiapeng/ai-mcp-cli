import React, { useCallback, useRef, useState } from 'react'
import ReactFlow, {
  Node, Edge, Connection, addEdge,
  useNodesState, useEdgesState,
  Controls, MiniMap, Background, BackgroundVariant,
  NodeTypes, ReactFlowInstance,
} from 'reactflow'
import { useFlowStore, useExecutionStore } from '../../store'
import { dslToGraph, graphToDsl } from '../../hooks/useApi'
import LobsterNode from './LobsterNode'
import DslEditor from './DslEditor'

const nodeTypes: NodeTypes = { lobsterNode: LobsterNode }

export default function FlowCanvas() {
  const { graph, setNodes: storeSetNodes, setEdges: storeSetEdges,
    selectNode, selectedNodeId, setGraph } = useFlowStore()
  const { dslText, setDsl, activeNodeId } = useExecutionStore()

  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges)
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null)
  const [showDsl, setShowDsl] = useState(false)
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  // Sync to store
  const syncNodes = useCallback((ns: Node[]) => {
    setNodes(ns)
    storeSetNodes(ns as any)
  }, [])

  const syncEdges = useCallback((es: Edge[]) => {
    setEdges(es)
    storeSetEdges(es as any)
  }, [])

  const onConnect = useCallback((params: Connection) => {
    const newEdges = addEdge({ ...params, type: 'smoothstep', animated: false }, edges)
    syncEdges(newEdges)
  }, [edges])

  // Drag-drop from NodeLibrary
  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    const raw = event.dataTransfer.getData('application/lobster-node')
    if (!raw || !rfInstance || !reactFlowWrapper.current) return

    const template = JSON.parse(raw)
    const bounds = reactFlowWrapper.current.getBoundingClientRect()
    const position = rfInstance.project({
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top,
    })

    const id = `node-${Date.now()}`
    const newNode: Node = {
      id,
      type: 'lobsterNode',
      position,
      data: {
        label: template.label,
        nodeType: template.type,
        args: template.defaultArgs,
        color: template.color,
        description: template.description,
      },
    }

    const updated = [...nodes, newNode]
    syncNodes(updated)
  }, [rfInstance, nodes])

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const onNodeClick = (_: any, node: Node) => {
    selectNode(node.id)
  }

  const handleDslImport = (dsl: string) => {
    const g = dslToGraph(dsl)
    setNodes(g.nodes)
    setEdges(g.edges)
    storeSetNodes(g.nodes as any)
    storeSetEdges(g.edges as any)
    setDsl(dsl)
  }

  const handleExportDsl = () => {
    const dsl = graphToDsl(nodes, edges)
    setDsl(dsl)
    setShowDsl(true)
  }

  // Highlight active node
  const displayNodes = nodes.map((n) => ({
    ...n,
    data: {
      ...n.data,
      isActive: activeNodeId !== null && n.id.includes(activeNodeId),
    },
  }))

  return (
    <div className="canvas-wrap" ref={reactFlowWrapper}>
      {/* Toolbar */}
      <div className="canvas-toolbar">
        <button className="btn" onClick={() => setShowDsl((v) => !v)}>
          {showDsl ? '📊 流程图' : '📝 DSL编辑器'}
        </button>
        <button className="btn" onClick={handleExportDsl}>导出 DSL</button>
        <button className="btn" onClick={() => {
          setNodes([])
          setEdges([])
          storeSetNodes([])
          storeSetEdges([])
        }}>清空</button>
        <button className="btn" onClick={() => rfInstance?.fitView()}>适应视图</button>
        <div style={{ flex: 1 }} />
        <span className="canvas-hint">拖拽左侧节点到画布 · 节点间连线 · 右键编辑</span>
      </div>

      {showDsl ? (
        <DslEditor
          value={dslText}
          onChange={setDsl}
          onImport={handleDslImport}
        />
      ) : (
        <ReactFlow
          nodes={displayNodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onInit={setRfInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode="Delete"
          multiSelectionKeyCode="Shift"
          snapToGrid
          snapGrid={[16, 16]}
        >
          <Controls position="bottom-right" />
          <MiniMap
            position="bottom-left"
            nodeColor={(n) => n.data?.color || '#444'}
            maskColor="rgba(13,17,23,0.7)"
          />
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#21262d" />
        </ReactFlow>
      )}

      <style>{`
        .canvas-wrap {
          flex: 1;
          display: flex;
          flex-direction: column;
          position: relative;
          background: var(--bg-base);
          overflow: hidden;
        }
        .canvas-toolbar {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 10px;
          background: var(--bg-surface);
          border-bottom: 1px solid var(--border);
          flex-shrink: 0;
        }
        .canvas-hint {
          font-size: 11px;
          color: var(--text-muted);
        }
      `}</style>
    </div>
  )
}
