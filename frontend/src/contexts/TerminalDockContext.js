import { createContext } from 'react'

// Lets AdminLayout announce "here is a visible spot to render the terminal into"
// while the actual <TerminalTabs/> instance lives permanently at the App root,
// so switching pages never unmounts it and open sessions survive navigation.
// Kept in its own file (no Provider/hook here) - react-refresh requires a
// file exporting a component to only export components, and the context
// object itself doesn't qualify as one.
export const TerminalDockContext = createContext(null)
