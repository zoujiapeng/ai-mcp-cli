import React, { useState } from 'react'
import { Play, Pause, Square, Zap, Save, FolderOpen, Settings } from 'lucide-react'
import { useExecutionStore, useFlowStore, useSettingsStore } from '../../store'
import { useApi, graphToDsl, dslToGraph } from '../../hooks/useApi'
import SettingsModal from './SettingsModal'

interface Props {
  backendOk: boolean
}

export default function TopBar({ backendOk }: Props) {
  const { state, dslText, setDsl, addLog, setTaskId } = useExecutionStore()
  const { graph, setGraph } = useFlowStore()
  const { apiKey } = useSettingsStore()
  const { runDsl, pauseExecution, resumeExecution, stopExecution, generateDsl } = useApi()
  const [aiInput, setAiInput] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const isRunning = state === 'running'
  const isPaused = state === 'paused'

  const handleRun = async () => {
    const dsl = dslText || graphToDsl(graph.nodes, graph.edges)
    if (!dsl.trim()) {
      addLog('warn', '请先输入 DSL 或构建流程图')
      return
    }
    try {
      const res = await runDsl(dsl)
      setTaskId(res.data.task_id)
      addLog('info', `任务已提交: ${res.data.task_id}`)
    } catch (e: any) {
      addLog('error', `提交失败: ${e.message}`)
    }
  }

  const handlePause = async () => {
    if (isPaused) await resumeExecution()
    else await pauseExecution()
  }

  const handleStop = async () => {
    await stopExecution()
    addLog('warn', '执行已停止')
  }

  const handleAiGenerate = async () => {
    if (!aiInput.trim()) return
    if (!apiKey) {
      addLog('error', '请先在设置中配置 API Key')
      return
    }
    setAiLoading(true)
    try {
      addLog('info', `🤖 AI 生成中: "${aiInput}"`)
      const res = await generateDsl(aiInput, apiKey)
      const { dsl, usage } = res.data
      setDsl(dsl)
      const g = dslToGraph(dsl)
      setGraph(g)
      addLog('success', `✅ DSL 生成完成 (输入:${usage.input_tokens} 输出:${usage.output_tokens} tokens)`)
    } catch (e: any) {
      addLog('error', `AI 生成失败: ${e.response?.data?.error || e.message}`)
    } finally {
      setAiLoading(false)
    }
  }

  return (
    <>
      <header className="topbar">
        {/* Logo */}
        <div className="topbar-logo">
          <span className="logo-icon">🦞</span>
          <span className="logo-text">Lobster</span>
          <span className="logo-version">v1.0</span>
        </div>

        {/* AI Input */}
        <div className="topbar-ai">
          <div className={`ai-input-wrap ${aiLoading ? 'loading' : ''}`}>
            <Zap size={14} className="ai-icon" />
            <input
              className="ai-input"
              placeholder="描述你的自动化任务，AI 生成 DSL..."
              value={aiInput}
              onChange={(e) => setAiInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAiGenerate()}
              disabled={aiLoading}
            />
            <button
              className="btn btn-primary ai-gen-btn"
              onClick={handleAiGenerate}
              disabled={aiLoading || !aiInput.trim()}
            >
              {aiLoading ? '生成中...' : 'AI生成'}
            </button>
          </div>
        </div>

        {/* Execution Controls */}
        <div className="topbar-controls">
          <button
            className="btn btn-success"
            onClick={handleRun}
            disabled={!backendOk || isRunning}
            title="运行 (F5)"
          >
            <Play size={13} />
            运行
          </button>

          <button
            className="btn"
            onClick={handlePause}
            disabled={!isRunning && !isPaused}
            title={isPaused ? '继续' : '暂停'}
          >
            <Pause size={13} />
            {isPaused ? '继续' : '暂停'}
          </button>

          <button
            className="btn btn-danger"
            onClick={handleStop}
            disabled={!isRunning && !isPaused}
            title="停止"
          >
            <Square size={13} />
            停止
          </button>

          <div className="topbar-sep" />

          <button className="btn btn-icon" title="打开">
            <FolderOpen size={14} />
          </button>
          <button className="btn btn-icon" title="保存">
            <Save size={14} />
          </button>
          <button className="btn btn-icon" onClick={() => setShowSettings(true)} title="设置">
            <Settings size={14} />
          </button>
        </div>
      </header>

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}

      <style>{`
        .topbar {
          height: var(--topbar-h);
          background: var(--bg-surface);
          border-bottom: 1px solid var(--border);
          display: flex;
          align-items: center;
          padding: 0 12px;
          gap: 12px;
          flex-shrink: 0;
          -webkit-app-region: drag;
        }
        .topbar > * { -webkit-app-region: no-drag; }

        .topbar-logo {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-shrink: 0;
        }
        .logo-icon { font-size: 18px; }
        .logo-text {
          font-weight: 700;
          font-size: 15px;
          color: var(--accent);
          letter-spacing: -0.5px;
        }
        .logo-version {
          font-size: 10px;
          color: var(--text-muted);
          background: var(--bg-hover);
          padding: 1px 5px;
          border-radius: 10px;
        }

        .topbar-ai { flex: 1; }
        .ai-input-wrap {
          display: flex;
          align-items: center;
          gap: 6px;
          background: var(--bg-elevated);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 0 8px;
          transition: border-color 0.15s;
        }
        .ai-input-wrap:focus-within { border-color: var(--accent-blue); }
        .ai-input-wrap.loading { opacity: 0.7; }
        .ai-icon { color: var(--accent-blue); flex-shrink: 0; }
        .ai-input {
          flex: 1;
          background: transparent;
          border: none;
          padding: 6px 0;
          font-size: 12.5px;
          color: var(--text-primary);
        }
        .ai-input:focus { outline: none; }
        .ai-gen-btn { border-radius: 4px; font-size: 11.5px; }

        .topbar-controls {
          display: flex;
          align-items: center;
          gap: 4px;
          flex-shrink: 0;
        }
        .topbar-sep {
          width: 1px;
          height: 20px;
          background: var(--border);
          margin: 0 4px;
        }
      `}</style>
    </>
  )
}
