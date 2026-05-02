import React, { useState } from 'react'
import { NODE_TEMPLATES } from '../../store'
import { NodeTemplate } from '@shared/types'

const CATEGORIES = [
  { key: 'action', label: '动作', icon: '⚡' },
  { key: 'control', label: '控制流', icon: '🔀' },
  { key: 'macro', label: '宏指令', icon: '🎯' },
  { key: 'perception', label: '感知', icon: '👁️' },
]

function NodeCard({ template, onDragStart }: { template: NodeTemplate; onDragStart: (e: React.DragEvent, t: NodeTemplate) => void }) {
  return (
    <div
      className="node-card"
      draggable
      onDragStart={(e) => onDragStart(e, template)}
      title={template.description}
    >
      <span className="node-card-icon">{template.icon}</span>
      <div className="node-card-info">
        <div className="node-card-label">{template.label}</div>
        <div className="node-card-desc">{template.description}</div>
      </div>
      <div
        className="node-card-dot"
        style={{ background: template.color }}
      />

      <style>{`
        .node-card {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 10px;
          border-radius: var(--radius);
          border: 1px solid var(--border-muted);
          background: var(--bg-elevated);
          cursor: grab;
          transition: all 0.12s;
          user-select: none;
        }
        .node-card:hover {
          border-color: var(--border);
          background: var(--bg-hover);
          transform: translateX(2px);
        }
        .node-card:active { cursor: grabbing; }
        .node-card-icon { font-size: 16px; flex-shrink: 0; }
        .node-card-info { flex: 1; min-width: 0; }
        .node-card-label { font-size: 12px; font-weight: 500; }
        .node-card-desc {
          font-size: 10.5px;
          color: var(--text-muted);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .node-card-dot {
          width: 6px; height: 6px;
          border-radius: 50%;
          flex-shrink: 0;
        }
      `}</style>
    </div>
  )
}

export default function NodeLibrary() {
  const [search, setSearch] = useState('')
  const [activeCategory, setActiveCategory] = useState<string | null>(null)

  const filtered = NODE_TEMPLATES.filter((t) => {
    const matchSearch = !search || t.label.includes(search) || t.description.includes(search)
    const matchCat = !activeCategory || t.category === activeCategory
    return matchSearch && matchCat
  })

  const onDragStart = (e: React.DragEvent, template: NodeTemplate) => {
    e.dataTransfer.setData('application/lobster-node', JSON.stringify(template))
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside className="node-library">
      <div className="lib-header">
        <span className="lib-title">节点库</span>
      </div>

      <div className="lib-search">
        <input
          placeholder="搜索节点..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="lib-cats">
        <button
          className={`cat-btn ${activeCategory === null ? 'active' : ''}`}
          onClick={() => setActiveCategory(null)}
        >全部</button>
        {CATEGORIES.map((c) => (
          <button
            key={c.key}
            className={`cat-btn ${activeCategory === c.key ? 'active' : ''}`}
            onClick={() => setActiveCategory(activeCategory === c.key ? null : c.key)}
          >
            {c.icon} {c.label}
          </button>
        ))}
      </div>

      <div className="lib-nodes">
        {CATEGORIES.map((cat) => {
          const nodes = filtered.filter((t) => t.category === cat.key)
          if (nodes.length === 0) return null
          return (
            <div key={cat.key} className="lib-section">
              <div className="lib-section-title">
                {cat.icon} {cat.label}
              </div>
              {nodes.map((t) => (
                <NodeCard key={t.id} template={t} onDragStart={onDragStart} />
              ))}
            </div>
          )
        })}
        {filtered.length === 0 && (
          <div className="lib-empty">未找到节点</div>
        )}
      </div>

      <style>{`
        .node-library {
          width: var(--sidebar-w);
          flex-shrink: 0;
          background: var(--bg-surface);
          border-right: 1px solid var(--border);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .lib-header {
          padding: 10px 12px 6px;
          border-bottom: 1px solid var(--border-muted);
        }
        .lib-title {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          color: var(--text-secondary);
        }
        .lib-search { padding: 8px; }
        .lib-search input { font-size: 12px; }

        .lib-cats {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          padding: 0 8px 8px;
        }
        .cat-btn {
          padding: 3px 8px;
          border-radius: 12px;
          border: 1px solid var(--border);
          background: transparent;
          color: var(--text-secondary);
          font-size: 11px;
          cursor: pointer;
          transition: all 0.1s;
        }
        .cat-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
        .cat-btn.active {
          background: var(--accent-blue);
          border-color: var(--accent-blue);
          color: #fff;
        }

        .lib-nodes {
          flex: 1;
          overflow-y: auto;
          padding: 0 8px 8px;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .lib-section { display: flex; flex-direction: column; gap: 4px; }
        .lib-section-title {
          font-size: 10px;
          font-weight: 600;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.6px;
          padding: 8px 2px 4px;
        }
        .lib-empty {
          color: var(--text-muted);
          font-size: 12px;
          text-align: center;
          padding: 24px;
        }
      `}</style>
    </aside>
  )
}
