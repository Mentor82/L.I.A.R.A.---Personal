import { createContext, useContext, useState } from 'react'

// Lets AdminLayout announce "here is a visible spot to render the terminal into"
// while the actual <TerminalTabs/> instance lives permanently at the App root,
// so switching pages never unmounts it and open sessions survive navigation.
const TerminalDockContext = createContext(null)

export function TerminalDockProvider({ children }) {
  const [dockNode, setDockNode] = useState(null)

  return (
    <TerminalDockContext.Provider value={{ dockNode, setDockNode }}>
      {children}
    </TerminalDockContext.Provider>
  )
}

export function useTerminalDock() {
  return useContext(TerminalDockContext)
}
