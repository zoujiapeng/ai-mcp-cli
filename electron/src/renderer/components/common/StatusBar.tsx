import React from 'react'
import { useExecutionStore } from '../../store'

interface Props {
  backendOk: boolean
  onToggleLog: () => void
}

const STATE_DOTS: Record<string, string> = {
  idle: '🔘',
  running: '🟢',
  paused: '🟡',
  stopped: '⏹',
  error: '🔴',
  finished: '✅',
}

export default function StatusBar({ backendOk, onToggleLog }: Props) {
  const { state, logs } = useExecutionStore()
  const lastLog = logs.length > 0 ? logs[logs.length - 1] : null

  return (
    <footer className="statusbar">
      <div className="statusbar-left">
        <span className={`status-dot ${backendOk ? 'ok' : 'err'}`} />
        <span className="status-text">
          {backendOk ? '后端已连接' : '后端未连接'}
        </span>
        <span className="statusbar-sep" />
        <span>{STATE_DOTS[state] || '🔘'}</span>
        <span className="status-text">{state.toUpperCase()}</span>
      </div>

      <div className="statusbar-center" onClick={onToggleLog}>
        {lastLog && (
          <span className="status-log-preview">
            {lastLog.message.slice(0, 60)}
            {lastLog.message.length > 60 ? '…' : ''}
          </span>
        )}
      </div>

      <div className="statusbar-right">
        <span className="status-text">Lobster v1.0</span>
      </div>

      <style>{`
        .statusbar {
          height: var(--statusbar-h);
          background: var(--bg-surface);
          border-top: 1px solid var(--border);
          display: flex;
          align-items: center;
          padding: 0 10px;
          gap: 8px;
          flex-shrink: 0;
          font-size: 11px;
        }
        .statusbar-left, .statusbar-right {
          display: flex;
          align-items: center;
          gap: 5px;
        }
        .statusbar-center {
          flex: 1;
          text-align: center;
          cursor: pointer;
          overflow: hidden;
          white-space: nowrap;
        }
        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
        }
        .status-dot.ok { background: var(--accent-green); }
        .status-dot.err { background: #da3633; }
        .status-text { color: var(--text-muted); }
        .statusbar-sep {
          width: 1px;
          height: 12px;
          background: var(--border);
        }
        .status-log-preview {
          color: var(--text-muted);
          font-size: 10.5px;
          font-family: var(--font-mono);
        }
      `}</style>
    </footer>
  )
}
