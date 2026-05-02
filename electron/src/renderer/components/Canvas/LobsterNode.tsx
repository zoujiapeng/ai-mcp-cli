import React, { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { FlowNodeData } from '@shared/types'

const NODE_ICONS: Record<string, string> = {
  CLICK: '🖱️',
  WAIT: '⏳',
  LOOP: '🔄',
  IF: '🔀',
  CONDITION: '🔀',
  RUN: '⚡',
  MACRO: '⚡',
  START: '▶',
  END: '⏹',
  SEQUENCE: '📋',
}

function LobsterNode({ data, selected }: NodeProps<FlowNodeData>) {
  const icon = NODE_ICONS[data.nodeType] || '⬜'
  const color = data.color || '#444'
  const isActive = data.isActive
  const hasError = data.hasError

  return (
    <div
      className={`lb-node
        ${selected ? 'selected' : ''}
        ${isActive ? 'active' : ''}
        ${hasError ? 'error' : ''}
        type-${data.nodeType?.toLowerCase()}
      `}
    >
      <Handle type="target" position={Position.Top} className="lb-handle" />

      <div className="lb-node-accent" style={{ background: color }} />

      <div className="lb-node-content">
        <div className="lb-node-header">
          <span className="lb-node-icon">{icon}</span>
          <span className="lb-node-type">{data.nodeType}</span>
          {isActive && <span className="lb-node-pulse" />}
        </div>
        {data.args && (
          <div className="lb-node-args">{data.args}</div>
        )}
        {data.label && data.label !== data.nodeType && (
          <div className="lb-node-label">{data.label}</div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="lb-handle" />
      {data.nodeType === 'IF' || data.nodeType === 'CONDITION' ? (
        <Handle
          type="source"
          position={Position.Right}
          id="else"
          className="lb-handle lb-handle-else"
          style={{ top: '50%' }}
        />
      ) : null}

      <style>{`
        .lb-node {
          background: var(--bg-elevated);
          border: 1.5px solid var(--border);
          border-radius: 8px;
          min-width: 140px;
          max-width: 220px;
          position: relative;
          overflow: hidden;
          transition: border-color 0.15s, box-shadow 0.15s;
          cursor: pointer;
        }
        .lb-node.selected {
          border-color: var(--accent-blue);
          box-shadow: 0 0 0 2px rgba(88,166,255,0.25);
        }
        .lb-node.active {
          border-color: var(--accent-green);
          box-shadow: 0 0 12px rgba(63,185,80,0.4);
          animation: pulse-active 1s ease-in-out infinite;
        }
        .lb-node.error {
          border-color: #da3633;
          box-shadow: 0 0 8px rgba(218,54,51,0.4);
        }

        @keyframes pulse-active {
          0%, 100% { box-shadow: 0 0 8px rgba(63,185,80,0.3); }
          50% { box-shadow: 0 0 16px rgba(63,185,80,0.6); }
        }

        .lb-node-accent {
          position: absolute;
          top: 0; left: 0; right: 0;
          height: 2px;
        }
        .lb-node-content { padding: 8px 10px; }
        .lb-node-header {
          display: flex;
          align-items: center;
          gap: 5px;
          margin-bottom: 4px;
        }
        .lb-node-icon { font-size: 13px; }
        .lb-node-type {
          font-size: 10.5px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: var(--text-secondary);
        }
        .lb-node-pulse {
          width: 6px; height: 6px;
          border-radius: 50%;
          background: var(--accent-green);
          animation: blink 0.8s step-end infinite;
          margin-left: auto;
        }
        @keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0; } }

        .lb-node-args {
          font-size: 12px;
          font-weight: 500;
          color: var(--text-primary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          font-family: var(--font-mono);
        }
        .lb-node-label {
          font-size: 10.5px;
          color: var(--text-muted);
          margin-top: 2px;
        }

        .lb-handle {
          width: 8px !important;
          height: 8px !important;
          border: 2px solid var(--border) !important;
          background: var(--bg-elevated) !important;
          transition: border-color 0.1s;
        }
        .lb-handle:hover {
          border-color: var(--accent-blue) !important;
          background: var(--accent-blue) !important;
        }
        .lb-handle-else {
          background: var(--accent-pink) !important;
          border-color: var(--accent-pink) !important;
        }
      `}</style>
    </div>
  )
}

export default memo(LobsterNode)
