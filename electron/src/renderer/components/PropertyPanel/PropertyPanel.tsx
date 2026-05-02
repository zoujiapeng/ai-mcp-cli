import React, { useEffect, useState } from 'react'
import { useFlowStore, useExecutionStore } from '../../store'
import { FlowNodeData } from '@shared/types'
import { X } from 'lucide-react'

export default function PropertyPanel() {
  const { selectedNodeId, graph, updateNodeData } = useFlowStore()
  const { state, logs } = useExecutionStore()

  const selectedNode = graph.nodes.find((n) => n.id === selectedNodeId)
  const [draft, setDraft] = useState<Partial<FlowNodeData>>({})

  useEffect(() => {
    if (selectedNode) setDraft(selectedNode.data)
  }, [selectedNodeId])

  const handleSave = () => {
    if (selectedNodeId) updateNodeData(selectedNodeId, draft)
  }

  const recentLogs = [...logs].reverse().slice(0, 30)

  return (
    <aside className="props-panel">
      {/* Properties section */}
      {selectedNode ? (
        <div className="props-section">
          <div className="props-header">
            <span>属性</span>
            <span className="props-node-type">{selectedNode.data.nodeType}</span>
          </div>

          <div className="props-body">
            <div className="prop-group">
              <label>标签</label>
              <input
                value={draft.label || ''}
                onChange={(e) => setDraft({ ...draft, label: e.target.value })}
              />
            </div>

            <div className="prop-group">
              <label>参数</label>
              <textarea
                rows={3}
                value={draft.args || ''}
                onChange={(e) => setDraft({ ...draft, args: e.target.value })}
                placeholder={getArgsHint(selectedNode.data.nodeType)}
              />
              <div className="prop-hint">{getArgsHint(selectedNode.data.nodeType)}</div>
            </div>

            <div className="prop-group">
              <label>颜色</label>
              <div className="color-row">
                {['#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#ef4444', '#10b981', '#06b6d4'].map((c) => (
                  <button
                    key={c}
                    className={`color-dot ${draft.color === c ? 'active' : ''}`}
                    style={{ background: c }}
                    onClick={() => setDraft({ ...draft, color: c })}
                  />
                ))}
              </div>
            </div>

            <div className="prop-group">
              <label>描述</label>
              <input
                value={draft.description || ''}
                placeholder="节点说明（可选）"
                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              />
            </div>

            <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleSave}>
              应用更改
            </button>
          </div>
        </div>
      ) : (
        <div className="props-empty">
          <div className="props-empty-icon">🖱️</div>
          <div>点击节点查看属性</div>
        </div>
      )}

      {/* Execution Status */}
      <div className="exec-status">
        <div className="props-header">
          <span>执行状态</span>
          <span className={`status-badge status-${state}`}>{STATE_LABELS[state] || state}</span>
        </div>
      </div>

      <style>{`
        .props-panel {
          width: var(--props-w);
          flex-shrink: 0;
          background: var(--bg-surface);
          border-left: 1px solid var(--border);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .props-section { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
        .props-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 12px 8px;
          border-bottom: 1px solid var(--border-muted);
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.7px;
          color: var(--text-secondary);
          flex-shrink: 0;
        }
        .props-node-type {
          font-size: 10px;
          background: var(--bg-hover);
          padding: 2px 7px;
          border-radius: 10px;
          color: var(--accent-blue);
        }
        .props-body {
          flex: 1;
          overflow-y: auto;
          padding: 10px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .prop-group { display: flex; flex-direction: column; gap: 4px; }
        .prop-group label { font-size: 11px; color: var(--text-secondary); font-weight: 500; }
        .prop-hint { font-size: 10.5px; color: var(--text-muted); }

        .color-row { display: flex; gap: 6px; flex-wrap: wrap; }
        .color-dot {
          width: 20px; height: 20px;
          border-radius: 50%;
          border: 2px solid transparent;
          cursor: pointer;
          transition: border-color 0.1s, transform 0.1s;
        }
        .color-dot:hover { transform: scale(1.2); }
        .color-dot.active { border-color: var(--text-primary); }

        .props-empty {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 8px;
          color: var(--text-muted);
          font-size: 12px;
        }
        .props-empty-icon { font-size: 28px; opacity: 0.4; }

        .exec-status { border-top: 1px solid var(--border); flex-shrink: 0; }
        .status-badge {
          font-size: 10px;
          padding: 2px 8px;
          border-radius: 10px;
          font-weight: 600;
        }
        .status-idle { background: #21262d; color: var(--text-secondary); }
        .status-running { background: rgba(63,185,80,0.2); color: var(--accent-green); }
        .status-paused { background: rgba(210,153,34,0.2); color: var(--accent-yellow); }
        .status-error { background: rgba(218,54,51,0.2); color: #f85149; }
        .status-finished { background: rgba(88,166,255,0.2); color: var(--accent-blue); }
        .status-stopped { background: var(--bg-hover); color: var(--text-muted); }
      `}</style>
    </aside>
  )
}

const STATE_LABELS: Record<string, string> = {
  idle: '空闲',
  running: '▶ 运行中',
  paused: '⏸ 已暂停',
  stopped: '⏹ 已停止',
  error: '❌ 出错',
  finished: '✅ 完成',
}

function getArgsHint(nodeType: string): string {
  const hints: Record<string, string> = {
    CLICK: '可以是文字、图像名称或 x,y 坐标',
    WAIT: '文字:XXX | 图像:XXX | 稳定 | 变化 | 消失:XXX',
    LOOP: '循环标签名（可选）',
    IF: '条件同 WAIT 格式',
    CONDITION: '条件同 WAIT 格式',
    RUN: '宏名称: 副本 / 刷任务 / 领取奖励 / 自动恢复',
    MACRO: '宏名称',
  }
  return hints[nodeType] || ''
}
