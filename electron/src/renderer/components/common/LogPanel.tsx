import React, { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { useExecutionStore } from '../../store'

interface Props {
  onClose: () => void
}

const LEVEL_COLORS: Record<string, string> = {
  info: 'var(--text-secondary)',
  warn: 'var(--accent-yellow)',
  error: '#f85149',
  success: 'var(--accent-green)',
}

export default function LogPanel({ onClose }: Props) {
  const { logs, clearLogs } = useExecutionStore()
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [logs.length])

  return (
    <div className="log-panel">
      <div className="log-header">
        <span className="log-title">执行日志 ({logs.length})</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn btn-icon" onClick={clearLogs} title="清空日志" style={{ fontSize: 10, padding: '2px 6px' }}>
            清空
          </button>
          <button className="btn btn-icon" onClick={onClose} title="关闭日志面板">
            <X size={12} />
          </button>
        </div>
      </div>
      <div className="log-body" ref={containerRef}>
        {logs.length === 0 ? (
          <div className="log-empty">暂无日志，运行任务后将显示执行过程</div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="log-line" style={{ '--log-color': LEVEL_COLORS[log.level] } as React.CSSProperties}>
              <span className="log-time">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className="log-level">{log.level.toUpperCase()}</span>
              <span className="log-msg">{log.message}</span>
            </div>
          ))
        )}
      </div>

      <style>{`
        .log-panel {
          height: var(--logpanel-h);
          border-top: 1px solid var(--border);
          background: var(--bg-base);
          display: flex;
          flex-direction: column;
          flex-shrink: 0;
        }
        .log-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 4px 10px;
          background: var(--bg-surface);
          border-bottom: 1px solid var(--border-muted);
          flex-shrink: 0;
        }
        .log-title {
          font-size: 10.5px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: var(--text-secondary);
        }
        .log-body {
          flex: 1;
          overflow-y: auto;
          padding: 4px 0;
          font-family: var(--font-mono);
          font-size: 11px;
          line-height: 1.6;
        }
        .log-empty {
          color: var(--text-muted);
          text-align: center;
          padding: 16px;
          font-size: 11px;
        }
        .log-line {
          display: flex;
          gap: 8px;
          padding: 1px 10px;
          color: var(--text-secondary);
        }
        .log-line:hover { background: var(--bg-hover); }
        .log-time {
          color: var(--text-muted);
          flex-shrink: 0;
          width: 70px;
        }
        .log-level {
          flex-shrink: 0;
          width: 44px;
          font-weight: 600;
          color: var(--log-color, var(--text-secondary));
        }
        .log-msg {
          color: var(--text-primary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      `}</style>
    </div>
  )
}
