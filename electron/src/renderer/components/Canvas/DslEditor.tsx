import React, { useCallback } from 'react'

interface Props {
  value: string
  onChange: (val: string) => void
  onImport: (dsl: string) => void
}

export default function DslEditor({ value, onChange, onImport }: Props) {
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      onImport(value)
    }
  }, [value, onImport])

  return (
    <div className="dsl-editor">
      <div className="dsl-toolbar">
        <span className="dsl-title">DSL 编辑器</span>
        <span className="dsl-hint">Ctrl+Enter 导入流程图</span>
        <button className="btn btn-primary" onClick={() => onImport(value)} style={{ marginLeft: 'auto' }}>
          导入流程图
        </button>
      </div>
      <textarea
        className="dsl-textarea"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={`输入 Lobster DSL...\n\n示例:\nCLICK 开始游戏\nWAIT 加载完成\nLOOP 主循环\n  RUN 副本\n  WAIT 结算界面\nEND`}
        spellCheck={false}
      />

      <style>{`
        .dsl-editor {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .dsl-toolbar {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 10px;
          background: var(--bg-surface);
          border-bottom: 1px solid var(--border);
          flex-shrink: 0;
        }
        .dsl-title {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: var(--text-secondary);
        }
        .dsl-hint {
          font-size: 10.5px;
          color: var(--text-muted);
        }
        .dsl-textarea {
          flex: 1;
          background: var(--bg-base);
          border: none;
          border-radius: 0;
          color: var(--text-primary);
          font-family: var(--font-mono);
          font-size: 13px;
          line-height: 1.7;
          padding: 12px 14px;
          resize: none;
          outline: none;
          tab-size: 2;
        }
        .dsl-textarea:focus { border: none; }
      `}</style>
    </div>
  )
}
