import React from 'react'
import { X } from 'lucide-react'
import { useSettingsStore } from '../../store'

export default function SettingsModal({ onClose }: { onClose: () => void }) {
  const settings = useSettingsStore()

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span>⚙️ 设置</span>
          <button className="btn btn-icon" onClick={onClose}><X size={14} /></button>
        </div>
        <div className="modal-body">
          <label>Anthropic API Key</label>
          <input
            type="password"
            value={settings.apiKey}
            placeholder="sk-ant-..."
            onChange={(e) => settings.update({ apiKey: e.target.value })}
          />

          <label>后端地址</label>
          <input
            value={settings.backendUrl}
            onChange={(e) => settings.update({ backendUrl: e.target.value })}
          />

          <label>默认超时 (秒)</label>
          <input
            type="number"
            value={settings.defaultTimeout}
            onChange={(e) => settings.update({ defaultTimeout: Number(e.target.value) })}
          />

          <label>最大循环次数</label>
          <input
            type="number"
            value={settings.maxLoops}
            onChange={(e) => settings.update({ maxLoops: Number(e.target.value) })}
          />

          <label>重试次数</label>
          <input
            type="number"
            value={settings.retryLimit}
            onChange={(e) => settings.update({ retryLimit: Number(e.target.value) })}
          />
        </div>
        <div className="modal-footer">
          <button className="btn btn-primary" onClick={onClose}>保存关闭</button>
        </div>
      </div>

      <style>{`
        .modal-overlay {
          position: fixed; inset: 0;
          background: rgba(0,0,0,0.6);
          display: flex; align-items: center; justify-content: center;
          z-index: 1000;
        }
        .modal {
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          width: 420px;
          box-shadow: var(--shadow);
        }
        .modal-header {
          display: flex; align-items: center; justify-content: space-between;
          padding: 12px 16px;
          border-bottom: 1px solid var(--border);
          font-weight: 600;
        }
        .modal-body {
          padding: 16px;
          display: flex; flex-direction: column; gap: 8px;
        }
        .modal-body label {
          font-size: 11px; color: var(--text-secondary); margin-top: 4px;
        }
        .modal-footer {
          padding: 12px 16px;
          border-top: 1px solid var(--border);
          display: flex; justify-content: flex-end;
        }
      `}</style>
    </div>
  )
}
