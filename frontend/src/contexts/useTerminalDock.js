import { useContext } from 'react'
import { TerminalDockContext } from './TerminalDockContext'

export function useTerminalDock() {
  return useContext(TerminalDockContext)
}
