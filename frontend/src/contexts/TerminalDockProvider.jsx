import { useState } from 'react'
import { TerminalDockContext } from './TerminalDockContext'

export function TerminalDockProvider({ children }) {
  const [dockNode, setDockNode] = useState(null)

  return (
    <TerminalDockContext.Provider value={{ dockNode, setDockNode }}>
      {children}
    </TerminalDockContext.Provider>
  )
}
