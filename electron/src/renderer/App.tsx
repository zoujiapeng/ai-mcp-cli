import React, { useEffect, useState } from 'react'
import { ReactFlowProvider } from 'reactflow'
import NodeLibrary from './components/NodeLibrary/NodeLibrary'
import FlowCanvas from './components/Canvas/FlowCanvas'
import PropertyPanel from './components/PropertyPanel/PropertyPanel'
import TopBar from './components/common/TopBar'
import StatusBar from './components/common/StatusBar'
import LogPanel from './components/common/LogPanel'
import { useSocket, useApi } from './hooks/useApi'
import { useExecutionStore } from './store'
import 'reactflow/dist/style.css'
import './styles/global.css'

export default function App() {
  const { addLog } = useExecutionStore()
  const { health } = useApi()
  const socketRef = useSocket()
  const [backendOk, setBackendOk] = useState(false)
  const [showLog, setShowLog] = useState(true)

  useEffect(() => {
    const check = async () => {
      try {
        await health()
        setBackendOk(true)
        addLog('success', '后端服务已连接')
      } catch {
        addLog('warn', '后端服务未就绪，请确认 Python 服务已启动')
      }
    }
    check()
    const timer = setInterval(check, 5000)
    return () => clearInterval(timer)
  }, [])

  return (
    <ReactFlowProvider>
      <div className="app-shell">
        <TopBar backendOk={backendOk} />
        <div className="app-body">
          <NodeLibrary />
          <div className="canvas-area">
            <FlowCanvas />
            {showLog && <LogPanel onClose={() => setShowLog(false)} />}
          </div>
          <PropertyPanel />
        </div>
        <StatusBar backendOk={backendOk} onToggleLog={() => setShowLog((v) => !v)} />
      </div>
    </ReactFlowProvider>
  )
}
